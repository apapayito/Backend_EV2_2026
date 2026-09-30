from django.urls import path

from . import web_views

urlpatterns = [
    path('', web_views.home, name='home'),
    path('cursos/', web_views.course_list, name='courses'),
    path('cursos/<int:pk>/', web_views.course_detail, name='course_detail'),
    path('login/', web_views.login_view, name='login'),
    path('registro/', web_views.register_view, name='register'),
    path('logout/', web_views.logout_view, name='logout'),
    path('carro/', web_views.cart_view, name='cart'),
    path('carro/agregar/<int:pk>/', web_views.cart_add, name='cart_add'),
    path('carro/quitar/<int:pk>/', web_views.cart_remove, name='cart_remove'),
    path('carro/checkout/', web_views.checkout, name='checkout'),
    path('matriculas/', web_views.enrollments, name='enrollments'),
]