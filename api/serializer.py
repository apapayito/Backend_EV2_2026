from rest_framework import serializers

from .models import Area, Cart, CartItem, Course, Enrollment, EnrollmentOrder, OrderItem


class AreaSerializer(serializers.ModelSerializer):
   class Meta:
      model = Area
      fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
   area_name = serializers.CharField(source='area.name', read_only=True)

   class Meta:
      model = Course
      fields = ('id', 'area', 'area_name', 'title', 'description', 'price', 'start_date', 'end_date',
              'capacity', 'available_seats', 'is_active')
      read_only_fields = ('available_seats',)

   def create(self, validated_data):
      validated_data['available_seats'] = validated_data['capacity']
      return super().create(validated_data)


class CartItemSerializer(serializers.ModelSerializer):
   course_title = serializers.CharField(source='course.title', read_only=True)
   unit_price = serializers.DecimalField(source='course.price', max_digits=10, decimal_places=2, read_only=True)

   class Meta:
      model = CartItem
      fields = ('id', 'course', 'course_title', 'unit_price', 'quantity')


class CartSerializer(serializers.ModelSerializer):
   items = CartItemSerializer(many=True, read_only=True)

   class Meta:
      model = Cart
      fields = ('id', 'items', 'updated_at')


class OrderItemSerializer(serializers.ModelSerializer):
   class Meta:
      model = OrderItem
      fields = ('course', 'course_title', 'unit_price', 'quantity')


class EnrollmentOrderSerializer(serializers.ModelSerializer):
   items = OrderItemSerializer(many=True, read_only=True)

   class Meta:
      model = EnrollmentOrder
      fields = ('id', 'status', 'total', 'items', 'created_at', 'updated_at')
      read_only_fields = fields


class EnrollmentSerializer(serializers.ModelSerializer):
   course_title = serializers.CharField(source='course.title', read_only=True)

   class Meta:
      model = Enrollment
      fields = ('id', 'course', 'course_title', 'order', 'created_at')
      read_only_fields = fields
