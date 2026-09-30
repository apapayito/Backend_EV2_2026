from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Area, Cart, CartItem, Course, Enrollment, EnrollmentOrder


def cart_course_ids(request):
    if not request.user.is_authenticated:
        return set()
    return set(CartItem.objects.filter(cart__user=request.user).values_list('course_id', flat=True))


def purchased_course_ids(request):
    if not request.user.is_authenticated:
        return set()
    paid_statuses = [EnrollmentOrder.Status.PAID, EnrollmentOrder.Status.COMPLETED]
    return set(Enrollment.objects.filter(
        student=request.user,
        order__status__in=paid_statuses,
    ).values_list('course_id', flat=True))


def home(request):
    courses = Course.objects.filter(is_active=True).select_related('area').order_by('start_date')[:6]
    areas = Area.objects.order_by('name')[:4]
    return render(request, 'home.html', {
        'courses': courses,
        'areas': areas,
        'cart_course_ids': cart_course_ids(request),
        'purchased_course_ids': purchased_course_ids(request),
    })


def course_list(request):
    courses = Course.objects.filter(is_active=True).select_related('area').order_by('start_date')
    area_id = request.GET.get('area')
    query = request.GET.get('q', '').strip()
    if area_id:
        courses = courses.filter(area_id=area_id)
    if query:
        courses = courses.filter(title__icontains=query)
    return render(request, 'courses.html', {
        'courses': courses,
        'areas': Area.objects.order_by('name'),
        'selected_area': area_id,
        'query': query,
        'cart_course_ids': cart_course_ids(request),
        'purchased_course_ids': purchased_course_ids(request),
    })


def course_detail(request, pk):
    course = get_object_or_404(Course.objects.select_related('area'), pk=pk, is_active=True)
    return render(request, 'course_detail.html', {
        'course': course,
        'in_cart': course.id in cart_course_ids(request),
        'purchased': course.id in purchased_course_ids(request),
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return redirect(request.GET.get('next') or 'home')
        messages.error(request, 'El usuario o la contraseña no son correctos.')
    return render(request, 'login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirmation = request.POST.get('password_confirmation', '')
        errors = []
        if not username:
            errors.append('El nombre de usuario es obligatorio.')
        elif get_user_model().objects.filter(username__iexact=username).exists():
            errors.append('Ese nombre de usuario ya está registrado.')
        if not email:
            errors.append('El correo electrónico es obligatorio.')
        if password != password_confirmation:
            errors.append('Las contraseñas no coinciden.')
        if not errors:
            try:
                validate_password(password)
            except Exception as error:
                translations = {
                    'this password is too short. it must contain at least 8 characters.':
                        'La contraseña es demasiado corta. Debe contener al menos 8 caracteres.',
                    'this password is too common.': 'La contraseña es demasiado común.',
                    'this password is entirely numeric.': 'La contraseña no puede estar formada solo por números.',
                    'the password is too similar to the username.':
                        'La contraseña es demasiado parecida al nombre de usuario.',
                }
                errors.extend(translations.get(message.lower(), message) for message in error.messages)
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            user = get_user_model().objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, 'Cuenta creada correctamente. Bienvenido a Nexo Academy.')
            return redirect('home')
    return render(request, 'register.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('course', 'course__area').all()
    total = sum(item.course.price * item.quantity for item in items)
    return render(request, 'cart.html', {'cart': cart, 'items': items, 'total': total})


@require_POST
@login_required
def cart_add(request, pk):
    course = get_object_or_404(Course, pk=pk, is_active=True)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
    if quantity != 1:
        messages.error(request, 'Cada curso puede agregarse una sola vez al carro.')
        return redirect('course_detail', pk=course.pk)
    paid_statuses = [EnrollmentOrder.Status.PAID, EnrollmentOrder.Status.COMPLETED]
    if Enrollment.objects.filter(student=request.user, course=course, order__status__in=paid_statuses).exists():
        messages.warning(request, 'Ya compraste este curso y no puedes matricularlo nuevamente.')
        return redirect('courses')
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if CartItem.objects.filter(cart=cart, course=course).exists():
        messages.warning(request, 'Este curso ya está en tu carro.')
        return redirect('courses')
    CartItem.objects.create(cart=cart, course=course, quantity=quantity)
    messages.success(request, f'{course.title} fue agregado a tu carro.')
    return redirect('courses')


@require_POST
@login_required
def cart_remove(request, pk):
    CartItem.objects.filter(pk=pk, cart__user=request.user).delete()
    return redirect('cart')


@require_POST
@login_required
def checkout(request):
    with transaction.atomic():
        cart = Cart.objects.select_for_update().filter(user=request.user).first()
        items = list(cart.items.select_related('course').all()) if cart else []
        if not items:
            messages.warning(request, 'Tu carro está vacío.')
            return redirect('cart')
        courses = {course.id: course for course in Course.objects.select_for_update().filter(
            id__in=[item.course_id for item in items], is_active=True
        )}
        paid_statuses = [EnrollmentOrder.Status.PAID, EnrollmentOrder.Status.COMPLETED]
        already_enrolled = Enrollment.objects.filter(
            student=request.user,
            course_id__in=courses,
            order__status__in=paid_statuses,
        ).exists()
        if already_enrolled:
            messages.error(request, 'Uno de los cursos ya fue comprado anteriormente.')
            return redirect('cart')
        if any(courses[item.course_id].available_seats < item.quantity for item in items):
            messages.error(request, 'Uno de los cursos no tiene cupos suficientes.')
            return redirect('cart')
        order = EnrollmentOrder.objects.create(user=request.user, status=EnrollmentOrder.Status.PAID)
        for item in items:
            course = courses[item.course_id]
            course.available_seats -= item.quantity
            course.save(update_fields=['available_seats'])
            from .models import OrderItem
            OrderItem.objects.create(order=order, course=course, course_title=course.title,
                                     unit_price=course.price, quantity=item.quantity)
            for _ in range(item.quantity):
                Enrollment.objects.create(order=order, student=request.user, course=course)
        order.total = sum(item.course.price * item.quantity for item in items)
        order.stock_released = True
        order.save(update_fields=['total', 'stock_released'])
        cart.items.all().delete()
    messages.success(request, 'Tu matrícula fue confirmada correctamente.')
    return redirect('/matriculas/?comprado=1')


@login_required
def enrollments(request):
    orders = EnrollmentOrder.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at')
    return render(request, 'enrollments.html', {'orders': orders, 'purchase_success': request.GET.get('comprado') == '1'})


def custom_404(request, exception):
    return render(request, '404.html', status=404)