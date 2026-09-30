from django.conf import settings
from django.db import models


class UserProfile(models.Model):
	"""Define el rol de negocio de cada usuario autenticado."""

	class Role(models.TextChoices):
		STUDENT = 'STUDENT', 'Estudiante'
		COORDINATOR = 'COORDINATOR', 'Coordinador Académico'

	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
	role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)


class Area(models.Model):
	name = models.CharField(max_length=120, unique=True)
	description = models.TextField(blank=True)

	def __str__(self):
		return self.name


class Course(models.Model):
	area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name='courses')
	title = models.CharField(max_length=180)
	description = models.TextField()
	price = models.DecimalField(max_digits=10, decimal_places=2)
	start_date = models.DateField()
	end_date = models.DateField()
	capacity = models.PositiveIntegerField(default=0)
	available_seats = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return self.title


class Cart(models.Model):
	"""Carro persistente: una sola instancia activa por usuario."""

	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
	updated_at = models.DateTimeField(auto_now=True)


class CartItem(models.Model):
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
	course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='cart_items')
	quantity = models.PositiveIntegerField(default=1)

	class Meta:
		constraints = [models.UniqueConstraint(fields=['cart', 'course'], name='unique_course_per_cart')]


class EnrollmentOrder(models.Model):
	class Status(models.TextChoices):
		PENDING = 'PENDING', 'Pendiente'
		PAID = 'PAID', 'Pagado'
		COMPLETED = 'COMPLETED', 'Completado'
		CANCELLED = 'CANCELLED', 'Cancelado'

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='enrollment_orders')
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	stock_released = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)


class OrderItem(models.Model):
	order = models.ForeignKey(EnrollmentOrder, on_delete=models.CASCADE, related_name='items')
	course = models.ForeignKey(Course, on_delete=models.PROTECT)
	course_title = models.CharField(max_length=180)
	unit_price = models.DecimalField(max_digits=10, decimal_places=2)
	quantity = models.PositiveIntegerField(default=1)


class Enrollment(models.Model):
	order = models.ForeignKey(EnrollmentOrder, on_delete=models.PROTECT, related_name='enrollments')
	student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='enrollments')
	course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='enrollments')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=['student', 'course', 'order'], name='unique_enrollment_per_order')]