from django.shortcuts import render, redirect
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
import requests

from .serializers import (
    SignupSerializer, 
    LoginSerializer, 
    ResetPasswordEmailSerializer, 
    ResetPasswordSerializer
)

User = get_user_model()

class SignupView(APIView):
    """
    API View to handle user registration.
    Expects name, roll_no, email, hall_of_residence, and password in request data.
    """
    authentication_classes = [] # Fix 401: allow without token
    permission_classes = [AllowAny]
    throttle_scope = 'signup' # Rate limit heavily

    def post(self, request):
        assert request.data is not None, "Request data must be provided"
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "User registered successfully.", "user_id": user.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    API View to handle user login.
    If credentials are valid, sets HttpOnly cookies containing the JWT tokens.
    """
    authentication_classes = [] # Fix 401: allow without token
    permission_classes = [AllowAny]

    def post(self, request):
        assert hasattr(settings, 'SIMPLE_JWT'), "SIMPLE_JWT configuration must be present in settings.py"
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            data = serializer.validated_data
            
            response = Response({
                "message": "Login successful.",
                "user": data['user'],
            }, status=status.HTTP_200_OK)
            
            # Set the access token as an HttpOnly cookie
            response.set_cookie(
                key=settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'),
                value=data['access'],
                expires=settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME', 0),
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
                httponly=True,
                samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
            )
            # You can also set refresh token in cookie if needed, keeping it simple here
            response.set_cookie(
                key="refresh_token",
                value=data['refresh'],
                expires=settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME', 0),
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
                httponly=True,
                samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
            )
            
            return response
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    def post(self, request):
        response = Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie(settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'))
        response.delete_cookie("refresh_token")
        return response


class ForgotPasswordView(APIView):
    """
    API View to handle the 'forgot password' flow.
    If the email exists, sends a reset password link via Brevo HTTP API.
    """
    authentication_classes = [] # Fix 401: allow without token
    permission_classes = [AllowAny]

    def post(self, request):
        assert request.data is not None, "Request data must be provided"
        serializer = ResetPasswordEmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            # Construct the reset link (pointing to our backend view)
            # We assume backend is running on HTTP_HOST 
            domain = request.META.get('HTTP_HOST', 'localhost:8000')
            reset_url = f"http://{domain}/api/reset-password/{uid}/{token}/"

            # Send Email via Brevo API
            brevo_api_key = getattr(settings, 'BREVO_API_KEY', None)
            
            if not brevo_api_key:
                 # fallback to simple printing for local development if forget to set key
                 print(f"PASSWORD RESET LINK for {user.email}: {reset_url}")
            else:
                self.send_brevo_email(email, user.name, reset_url)

            return Response({"message": "Password reset email sent if the account exists."}, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_brevo_email(self, to_email, to_name, reset_url):
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json"
        }
        payload = {
            "sender": {"email": settings.DEFAULT_FROM_EMAIL, "name": "CMMS Auth"},
            "to": [{"email": to_email, "name": to_name}],
            "subject": "Reset your Password",
            "htmlContent": f"<html><body><p>Hello {to_name},</p><p>Please click the link below to reset your password:</p><a href='{reset_url}'>{reset_url}</a></body></html>"
        }
        
        try:
             response = requests.post(url, json=payload, headers=headers)
             response.raise_for_status()
        except Exception as e:
             print(f"Failed to send email: {e}")


from django.views import View

class ResetPasswordTemplateView(View):
    """
    HTML Template View for the backend to reset the password.
    Users arrive here via the Brevo email link to securely change their password.
    """
    
    def get(self, request, uidb64, token):
        assert uidb64 and token, "Both UID and token must be present in the URL"
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            return render(request, "Backend_App/password_reset.html", {"validlink": True, "uidb64": uidb64, "token": token})
        else:
            return render(request, "Backend_App/password_reset.html", {"validlink": False})

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password and new_password == confirm_password and len(new_password) >= 8:
                user.set_password(new_password)
                user.save()
                # Redirect to frontend login on success
                return redirect('http://localhost:5173/login')
            else:
                error = "Passwords do not match or are less than 8 characters."
                return render(request, "Backend_App/password_reset.html", {
                    "validlink": True, 
                    "uidb64": uidb64, 
                    "token": token,
                    "error": error
                })
        else:
            return render(request, "Backend_App/password_reset.html", {"validlink": False})
