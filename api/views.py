from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Area, Cart, CartItem, Course, Enrollment, EnrollmentOrder, OrderItem
from .permissions import IsCoordinator
from .serializer import AreaSerializer, CartSerializer, CourseSerializer, EnrollmentOrderSerializer, EnrollmentSerializer


class AreaViewSet(viewsets.ModelViewSet):
	queryset = Area.objects.all()
	serializer_class = AreaSerializer
	permission_classes = [AllowAny]

	def get_permissions(self):
		return [AllowAny()] if self.request.method == 'GET' else [IsCoordinator()]


class CourseViewSet(viewsets.ModelViewSet):
	queryset = Course.objects.select_related('area').filter(is_active=True)
	serializer_class = CourseSerializer
	filter_backends = [DjangoFilterBackend]
	filterset_fields = {'area': ['exact'], 'price': ['gte', 'lte'], 'start_date': ['gte', 'lte']}
	permission_classes = [AllowAny]

	def get_permissions(self):
		return [AllowAny()] if self.request.method in ('GET', 'HEAD', 'OPTIONS') else [IsCoordinator()]


class CartViewSet(viewsets.ViewSet):
	queryset = CartItem.objects.none()
	permission_classes = [IsAuthenticated]
	serializer_class = CartSerializer

	def list(self, request):
		cart, _ = Cart.objects.get_or_create(user=request.user)
		return Response(CartSerializer(cart).data)

	def create(self, request):
		course_id = request.data.get('course')
		try:
			quantity = int(request.data.get('quantity', 1))
		except (TypeError, ValueError):
			quantity = 0
		if quantity != 1:
			return Response({'detail': 'Cada curso puede agregarse una sola vez al carro.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			course = Course.objects.get(pk=course_id, is_active=True)
		except Course.DoesNotExist:
			return Response({'detail': 'Curso no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
		paid_statuses = [EnrollmentOrder.Status.PAID, EnrollmentOrder.Status.COMPLETED]
		if Enrollment.objects.filter(student=request.user, course=course, order__status__in=paid_statuses).exists():
			return Response({'detail': 'Este curso ya fue comprado anteriormente.'}, status=status.HTTP_400_BAD_REQUEST)
		cart, _ = Cart.objects.get_or_create(user=request.user)
		if CartItem.objects.filter(cart=cart, course=course).exists():
			return Response({'detail': 'Este curso ya está en tu carro.'}, status=status.HTTP_400_BAD_REQUEST)
		CartItem.objects.create(cart=cart, course=course, quantity=quantity)
		return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)

	def destroy(self, request, pk=None):
		deleted, _ = CartItem.objects.filter(cart__user=request.user, pk=pk).delete()
		if not deleted:
			return Response({'detail': 'Ítem no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
		return Response(status=status.HTTP_204_NO_CONTENT)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = EnrollmentOrder.objects.none()
	serializer_class = EnrollmentOrderSerializer
	permission_classes = [IsAuthenticated]

	def get_queryset(self):
		if getattr(self, 'swagger_fake_view', False):
			return EnrollmentOrder.objects.none()
		queryset = EnrollmentOrder.objects.prefetch_related('items')
		if self.request.user.is_staff:
			return queryset
		return queryset.filter(user=self.request.user)

	@action(detail=False, methods=['post'], url_path='checkout')
	def checkout(self, request):
		with transaction.atomic():
			cart = Cart.objects.select_for_update().filter(user=request.user).first()
			items = list(cart.items.select_related('course').all()) if cart else []
			if not items:
				return Response({'detail': 'El carro está vacío.'}, status=status.HTTP_400_BAD_REQUEST)
			course_ids = [item.course_id for item in items]
			locked_courses = {
				course.id: course for course in Course.objects.select_for_update().filter(id__in=course_ids)
			}
			paid_statuses = [EnrollmentOrder.Status.PAID, EnrollmentOrder.Status.COMPLETED]
			if Enrollment.objects.filter(
				student=request.user,
				course_id__in=locked_courses,
				order__status__in=paid_statuses,
			).exists():
				return Response({'detail': 'Uno de los cursos ya fue comprado anteriormente.'}, status=status.HTTP_400_BAD_REQUEST)
			for item in items:
				course = locked_courses[item.course_id]
				if course.available_seats < item.quantity:
					return Response({'detail': f'No hay cupos suficientes para {course.title}.'}, status=status.HTTP_409_CONFLICT)

			order = EnrollmentOrder.objects.create(user=request.user, status=EnrollmentOrder.Status.PAID)
			total = 0
			for item in items:
				course = locked_courses[item.course_id]
				course.available_seats -= item.quantity
				course.save(update_fields=['available_seats'])
				OrderItem.objects.create(order=order, course=course, course_title=course.title,
										 unit_price=course.price, quantity=item.quantity)
				for _ in range(item.quantity):
					Enrollment.objects.create(order=order, student=request.user, course=course)
				total += course.price * item.quantity
			order.total = total
			order.stock_released = True
			order.save(update_fields=['total', 'stock_released'])
			cart.items.all().delete()
		return Response(EnrollmentOrderSerializer(order).data, status=status.HTTP_201_CREATED)

	@action(detail=True, methods=['patch'], url_path='estado', permission_classes=[IsCoordinator])
	def estado(self, request, pk=None):
		new_status = request.data.get('status')
		valid_statuses = {choice[0] for choice in EnrollmentOrder.Status.choices}
		if new_status not in valid_statuses:
			return Response({'detail': 'Estado inválido.'}, status=status.HTTP_400_BAD_REQUEST)
		with transaction.atomic():
			order = EnrollmentOrder.objects.select_for_update().prefetch_related('items').get(pk=pk)
			if order.status == EnrollmentOrder.Status.CANCELLED:
				return Response({'detail': 'La orden ya está cancelada.'}, status=status.HTTP_400_BAD_REQUEST)
			allowed_transitions = {
				EnrollmentOrder.Status.PENDING: {EnrollmentOrder.Status.CANCELLED},
				EnrollmentOrder.Status.PAID: {EnrollmentOrder.Status.COMPLETED, EnrollmentOrder.Status.CANCELLED},
				EnrollmentOrder.Status.COMPLETED: set(),
			}
			if new_status not in allowed_transitions.get(order.status, set()):
				return Response({'detail': f'Transición no permitida desde {order.status}.'},
								status=status.HTTP_400_BAD_REQUEST)
			if new_status == EnrollmentOrder.Status.CANCELLED and order.stock_released:
				for item in order.items.select_related('course'):
					course = Course.objects.select_for_update().get(pk=item.course_id)
					course.available_seats += item.quantity
					course.save(update_fields=['available_seats'])
				order.stock_released = False
			order.status = new_status
			order.save(update_fields=['status', 'stock_released', 'updated_at'])
		return Response(EnrollmentOrderSerializer(order).data)


class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Enrollment.objects.none()
	serializer_class = EnrollmentSerializer
	permission_classes = [IsAuthenticated]

	def get_queryset(self):
		if getattr(self, 'swagger_fake_view', False):
			return Enrollment.objects.none()
		return Enrollment.objects.filter(student=self.request.user).select_related('course', 'order')