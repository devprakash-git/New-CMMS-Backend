import re
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['name', 'roll_no', 'email', 'hall_of_residence', 'password']

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
            roll_no=validated_data['roll_no'],
            hall_of_residence=validated_data['hall_of_residence'],
            password=validated_data['password']
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Authenticates user with given credentials."""
        email = attrs.get('email')
        password = attrs.get('password')
        assert email and password, "Email and password must both be provided for extraction"

        user = authenticate(request=self.context.get('request'), email=email, password=password)
        if not user:
            raise AuthenticationFailed("Invalid email or password.")
        
        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")

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
                'hall_of_residence': user.hall_of_residence
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
