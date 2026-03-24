import re
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed

from .models import Hall, Notification, Menu, Feedback, RebateApp, MyBooking, Booking, Cart, DailyRebateRefund

User = get_user_model()

class HallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = ['id', 'name']

class UserProfileSerializer(serializers.ModelSerializer):
    hall_of_residence = serializers.CharField(source='hall_of_residence.name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'roll_no', 'hall_of_residence', 'room_no', 'contact_no', 'role']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'content', 'category', 'time']

class MenuSerializer(serializers.ModelSerializer):
    hall_name = serializers.CharField(source='hall.name', read_only=True)

    class Meta:
        model = Menu
        fields = ['id', 'hall', 'hall_name', 'day', 'meal_time', 'dish']

class FeedbackSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Feedback
        fields = ['id', 'user', 'user_name', 'user_email', 'category', 'date', 'status', 'content']
        read_only_fields = ['id', 'user', 'date', 'status']


class RebateAppSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = RebateApp
        fields = ['id', 'user', 'user_name', 'user_email', 'start_date', 'end_date', 'location', 'created_at', 'status']
        read_only_fields = ['id', 'user', 'created_at', 'status']

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['name', 'roll_no', 'email', 'hall_of_residence', 'room_no', 'contact_no', 'role', 'password']

    def validate_email(self, value):
        """Validates that the provided email ends with the designated @iitk.ac.in domain."""
        assert isinstance(value, str), "Email must be a string"
        if not value.endswith('@iitk.ac.in'):
            raise serializers.ValidationError("Email must end with @iitk.ac.in")
        return value

    def create(self, validated_data):
        """Create a new user using the validated data."""
        assert 'password' in validated_data, "Password must be provided to create a user"
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            roll_no=validated_data.get('roll_no', ''),
            hall_of_residence=validated_data.get('hall_of_residence', ''),
            room_no=validated_data.get('room_no', ''),
            contact_no=validated_data.get('contact_no', ''),
            role=validated_data.get('role', 'student'),
            password=validated_data['password']
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(required=False)

    def validate(self, attrs):
        """Authenticates user with given credentials."""
        email = attrs.get('email')
        password = attrs.get('password')
        role = attrs.get('role')
        assert email and password, "Email and password must both be provided for extraction"

        user = authenticate(request=self.context.get('request'), email=email, password=password)
        if not user:
            raise AuthenticationFailed("Invalid email or password.")
        
        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        if role and user.role != role:
            raise AuthenticationFailed(f"Please use the correct login portal for your role ({user.role}).")

        refresh = RefreshToken.for_user(user)
        assert refresh is not None, "Failed to generate JWT token"

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'roll_no': user.roll_no,
                'hall_of_residence': user.hall_of_residence.name if user.hall_of_residence else '',
                'role': user.role
            }
        }


class ResetPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """Ensure the email is registered before sending a reset link."""
        assert isinstance(value, str), "Email must be a string formatted value."
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user is associated with this email address.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        """Validates that both passwords match."""
        new_pw = attrs.get('new_password')
        confirm_pw = attrs.get('confirm_password')
        assert new_pw is not None and confirm_pw is not None, "Passwords must not be None"

        if new_pw != confirm_pw:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs


class MyBookingSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='booking.item.name', read_only=True)
    item_cost = serializers.DecimalField(source='booking.item.cost', max_digits=10, decimal_places=2, read_only=True)
    month = serializers.CharField(source='booking.item.month', read_only=True)

    class Meta:
        model = MyBooking
        fields = ['id', 'item_name', 'item_cost', 'month', 'quantity', 'status', 'booked_at', 'qr_code_id']

class BookingSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_cost = serializers.DecimalField(source='item.cost', max_digits=10, decimal_places=2, read_only=True)
    hall_name = serializers.CharField(source='hall.name', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'item', 'item_name', 'item_cost', 'hall', 'hall_name', 'day_and_time', 'available_count']

class CartSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_cost = serializers.DecimalField(source='item.cost', max_digits=10, decimal_places=2, read_only=True)
    available_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'item', 'item_name', 'item_cost', 'quantity', 'available_count']

    def get_available_count(self, obj):
        from .models import Booking
        user = obj.user
        user_hall = user.hall_of_residence
        
        bookings = Booking.objects.filter(item=obj.item)
        if user_hall:
            hall_bookings = bookings.filter(hall=user_hall)
            if hall_bookings.exists():
                bookings = hall_bookings
        
        booking = bookings.order_by('day_and_time').first()
        return booking.available_count if booking else 0

class DailyRebateRefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyRebateRefund
        fields = ['id', 'month', 'cost']
