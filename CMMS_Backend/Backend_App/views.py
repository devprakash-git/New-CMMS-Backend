from django.shortcuts import render, redirect
from django.conf import settings
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
import requests

from django.db.models import Sum
from .models import Hall, Notification, Menu, Feedback, RebateApp, FixedCharges, MyBooking, DailyRebateRefund
from .serializers import (
    SignupSerializer, 
    LoginSerializer, 
    ResetPasswordEmailSerializer, 
    ResetPasswordSerializer,
    HallSerializer,
    UserProfileSerializer,
    NotificationSerializer,
    MenuSerializer,
    FeedbackSerializer,
    RebateAppSerializer,
    MyBookingSerializer
)

User = get_user_model()

class HallListView(APIView):
    """
    API View to return a list of all halls.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        halls = Hall.objects.all()
        serializer = HallSerializer(halls, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    """
    API View to return the authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthStatusView(APIView):
    """
    API View to check if the current user is logged in (the "My" API).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user and request.user.is_authenticated:
            serializer = UserProfileSerializer(request.user)
            return Response({
                "is_logged_in": True,
                "user": serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            "is_logged_in": False,
            "user": None
        }, status=status.HTTP_200_OK)


class NotificationListView(APIView):
    """
    API View to return notifications for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-time')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MenuListView(APIView):
    """
    API View to return the weekly mess menu.
    Allows filtering by hall_id query parameter. 
    Defaults to returning menu for the user's hall.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        hall_id = request.query_params.get('hall_id')
        if hall_id:
            menus = Menu.objects.filter(hall_id=hall_id)
        else:
            # Default to user's hall if available, else all menus
            if getattr(request.user, 'hall_of_residence', None):
                menus = Menu.objects.filter(hall=request.user.hall_of_residence)
            else:
                menus = Menu.objects.all()

        serializer = MenuSerializer(menus, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MarkNotificationsSeenView(APIView):
    """
    API View to mark all unseen notifications as seen for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated_count = Notification.objects.filter(user=request.user, category='unseen').update(category='seen')
        return Response({"message": f"{updated_count} notifications marked as seen."}, status=status.HTTP_200_OK)


class FeedbackListView(APIView):
    """
    API View to list and create feedbacks.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') == 'admin':
            feedbacks = Feedback.objects.all().order_by('-date', '-id')
        else:
            feedbacks = Feedback.objects.filter(user=request.user).order_by('-date', '-id')
        
        serializer = FeedbackSerializer(feedbacks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RebateAppListView(APIView):
    """
    API View to list and create Rebate Applications.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') == 'admin':
            rebates = RebateApp.objects.all().order_by('-created_at', '-id')
        else:
            rebates = RebateApp.objects.filter(user=request.user).order_by('-created_at', '-id')
        
        serializer = RebateAppSerializer(rebates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RebateAppSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyBookingListView(APIView):
    """
    API View to list items booked by the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = MyBooking.objects.filter(user=request.user).select_related('booking__item').order_by('-booked_at')
        serializer = MyBookingSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MessBillView(APIView):
    """
    API View to calculate and return the Monthly Mess Bill.
    Bill = MyBooking item costs + FixedCharges - Rebate refund.
    """
    permission_classes = [IsAuthenticated]

    def _get_rebate_days_for_month(self, user, month_str):
        """
        Calculate total rebate days for a user in a given month (e.g. 'March').
        Assumes the current year. Finds all approved rebates that overlap with the calendar month.
        """
        import calendar
        from datetime import date

        year = date.today().year

        try:
            month_num = list(calendar.month_name).index(month_str)
        except (ValueError, IndexError):
            return 0

        month_start = date(year, month_num, 1)
        month_end = date(year, month_num, calendar.monthrange(year, month_num)[1])

        approved_rebates = RebateApp.objects.filter(
            user=user,
            status='approved',
            start_date__lte=month_end,
            end_date__gte=month_start
        )

        total_days = 0
        for rebate in approved_rebates:
            overlap_start = max(rebate.start_date, month_start)
            overlap_end = min(rebate.end_date, month_end)
            total_days += (overlap_end - overlap_start).days + 1

        return total_days

    def get(self, request):
        user = request.user
        target_month = request.query_params.get('month')
        
        fixed_charges_qs = FixedCharges.objects.filter(user=user)
        total_fixed_charges = fixed_charges_qs.aggregate(total=Sum('bill'))['total'] or 0
        fixed_charges_list = list(fixed_charges_qs.values('hall__name', 'category', 'bill'))

        bookings = MyBooking.objects.filter(user=user, status='confirmed').select_related('booking__item')
        if target_month:
            bookings = bookings.filter(booking__item__month=target_month)
            
        bills_by_month = {}
        
        for mb in bookings:
            item = mb.booking.item
            month = item.month
            cost = mb.quantity * item.cost
            
            if month not in bills_by_month:
                bills_by_month[month] = {"items": [], "total_item_cost": 0}
                
            bills_by_month[month]["items"].append({
                "item_name": item.name,
                "quantity": mb.quantity,
                "cost_per_item": item.cost,
                "total_cost": cost,
                "date": mb.booked_at
            })
            bills_by_month[month]["total_item_cost"] += cost
            
        response_data = []
        if target_month and target_month not in bills_by_month:
            bills_by_month[target_month] = {"items": [], "total_item_cost": 0}

        for month, data in bills_by_month.items():
            # Calculate rebate refund for this month
            rebate_days = self._get_rebate_days_for_month(user, month)
            daily_refund_obj = DailyRebateRefund.objects.filter(month=month).first()
            daily_refund_rate = daily_refund_obj.cost if daily_refund_obj else 0
            rebate_refund = rebate_days * daily_refund_rate

            total_bill = data["total_item_cost"] + total_fixed_charges - rebate_refund
            response_data.append({
                "month": month,
                "total_item_cost": data["total_item_cost"],
                "total_fixed_charges": total_fixed_charges,
                "rebate_days": rebate_days,
                "daily_refund_rate": daily_refund_rate,
                "rebate_refund": rebate_refund,
                "total_bill": total_bill,
                "fixed_charges_details": fixed_charges_list,
                "items_bought": data["items"]
            })
            
        return Response(response_data, status=status.HTTP_200_OK)


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
            scheme = request.scheme
            reset_url = f"{scheme}://{domain}/api/reset-password/{uid}/{token}/"

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
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
                return redirect(f"{frontend_url}/login")
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
