from datetime import date

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase
from .authentication import RoleTokenObtainPairSerializer
from .models import Area, CartItem, Course, EnrollmentOrder, UserProfile


class EdTechFlowTests(APITestCase):
	def setUp(self):
		self.student = get_user_model().objects.create_user(username='student', password='password123')
		self.area = Area.objects.create(name='Backend')
		self.course = Course.objects.create(
			area=self.area,
			title='Django REST',
			description='API y persistencia',
			price=50000,
			start_date=date(2026, 10, 1),
			end_date=date(2026, 11, 1),
			capacity=2,
			available_seats=2,
		)

	def test_jwt_includes_student_role(self):
		token = RoleTokenObtainPairSerializer.get_token(self.student)
		self.assertEqual(token['role'], UserProfile.Role.STUDENT)

	def test_cart_persists_and_checkout_discounts_seats(self):
		self.client.force_authenticate(self.student)
		self.client.post('/api/carrito/', {'course': self.course.id, 'quantity': 1}, format='json')
		self.assertTrue(CartItem.objects.filter(cart__user=self.student, course=self.course).exists())

		response = self.client.post('/api/ordenes/checkout/', format='json')
		self.assertEqual(response.status_code, 201)
		self.course.refresh_from_db()
		self.assertEqual(self.course.available_seats, 1)
		self.assertEqual(EnrollmentOrder.objects.get(user=self.student).status, EnrollmentOrder.Status.PAID)
		second_attempt = self.client.post('/api/carrito/', {'course': self.course.id}, format='json')
		self.assertEqual(second_attempt.status_code, 400)

	def test_same_course_cannot_be_added_twice(self):
		self.client.force_authenticate(self.student)
		first_response = self.client.post('/api/carrito/', {'course': self.course.id}, format='json')
		second_response = self.client.post('/api/carrito/', {'course': self.course.id}, format='json')
		self.assertEqual(first_response.status_code, 201)
		self.assertEqual(second_response.status_code, 400)
		self.assertEqual(CartItem.objects.filter(cart__user=self.student, course=self.course).count(), 1)

	def test_coordinator_cancelling_order_restores_seats(self):
		self.client.force_authenticate(self.student)
		self.client.post('/api/carrito/', {'course': self.course.id, 'quantity': 1}, format='json')
		checkout = self.client.post('/api/ordenes/checkout/', format='json')
		order_id = checkout.data['id']

		coordinator = get_user_model().objects.create_user(username='coordinator', password='password123')
		coordinator.profile.role = UserProfile.Role.COORDINATOR
		coordinator.profile.save()
		self.client.force_authenticate(coordinator)
		response = self.client.patch(f'/api/ordenes/{order_id}/estado/', {'status': 'CANCELLED'}, format='json')

		self.assertEqual(response.status_code, 200)
		self.course.refresh_from_db()
		self.assertEqual(self.course.available_seats, 2)

	def test_home_and_404_redirect_are_available(self):
		response = self.client.get('/')
		self.assertEqual(response.status_code, 200)
		with override_settings(DEBUG=False):
			response = self.client.get('/ruta-inexistente/')
		self.assertEqual(response.status_code, 404)
		self.assertContains(response, 'Esta página no existe.', status_code=404)
		self.assertContains(response, 'Volver al inicio', status_code=404)

	def test_web_404_is_customized_with_debug_enabled(self):
		response = self.client.get('/otra-ruta-inexistente/')
		self.assertEqual(response.status_code, 404)
		self.assertContains(response, 'Esta página no existe.', status_code=404)

	def test_register_creates_student_account_and_profile(self):
		response = self.client.post('/registro/', {
			'username': 'newstudent',
			'email': 'newstudent@example.com',
			'password': 'StrongPassword123!',
			'password_confirmation': 'StrongPassword123!',
		}, follow=True)
		self.assertEqual(response.status_code, 200)
		user = get_user_model().objects.get(username='newstudent')
		self.assertTrue(user.check_password('StrongPassword123!'))
		self.assertEqual(user.profile.role, UserProfile.Role.STUDENT)

	def test_register_shows_password_warnings_in_spanish(self):
		response = self.client.post('/registro/', {
			'username': 'weakstudent',
			'email': 'weakstudent@example.com',
			'password': '123',
			'password_confirmation': '123',
		})
		self.assertContains(response, 'La contraseña es demasiado corta.')
		self.assertContains(response, 'Esta contraseña es demasiado común.')
		self.assertContains(response, 'Esta contraseña es completamente numérica.')
