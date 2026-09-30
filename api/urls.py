from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'areas', views.AreaViewSet, basename='area')
router.register(r'cursos', views.CourseViewSet, basename='curso')
router.register(r'carrito', views.CartViewSet, basename='carrito')
router.register(r'ordenes', views.OrderViewSet, basename='orden')
router.register(r'mis-matriculas', views.EnrollmentViewSet, basename='matricula')

urlpatterns = [
	path('', include(router.urls)),
]
