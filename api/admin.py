from django.contrib import admin

from .models import Area, Cart, CartItem, Course, Enrollment, EnrollmentOrder, OrderItem, UserProfile

admin.site.register((UserProfile, Area, Course, Cart, CartItem, EnrollmentOrder, OrderItem, Enrollment))