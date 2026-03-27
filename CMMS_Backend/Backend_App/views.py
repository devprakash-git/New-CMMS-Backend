from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
import requests
import uuid
import io
from django.utils import timezone
import calendar
from dataclasses import dataclass

from django.db.models import Sum
from .models import Hall, Notification, Menu, Feedback, RebateApp, FixedCharges, MyBooking, DailyRebateRefund, BillVerification, Booking, Cart, Item, BillPaymentStatus, QRDatabase
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
    MyBookingSerializer,
    BookingSerializer,
    CartSerializer,
    DailyRebateRefundSerializer,
    FixedChargesSerializer
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

class AdminMenuUpdateView(APIView):
    """
    API View for Admin to add or update a menu item.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        item_id = request.data.get('id')
        if item_id:
            try:
                menu_item = Menu.objects.get(id=item_id)
                serializer = MenuSerializer(menu_item, data=request.data, partial=True)
            except Menu.DoesNotExist:
                return Response({"error": "Menu item not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            serializer = MenuSerializer(data=request.data)
            
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK if item_id else status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminMenuDeleteView(APIView):
    """
    API View for Admin to delete a menu item.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            menu_item = Menu.objects.get(pk=pk)
            menu_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Menu.DoesNotExist:
            return Response({"error": "Menu item not found."}, status=status.HTTP_404_NOT_FOUND)


class MarkNotificationsSeenView(APIView):
    """
    API View to mark all unseen notifications as seen for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated_count = Notification.objects.filter(user=request.user, category='unseen').update(category='seen')
        return Response({"message": f"{updated_count} notifications marked as seen."}, status=status.HTTP_200_OK)


class AdminRebateStatusUpdateView(APIView):
    """
    API View for Admin to approve or reject rebate applications.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Unauthorized. Admin role required."}, status=status.HTTP_403_FORBIDDEN)
        
        rebate_id = request.data.get('rebate_id')
        new_status = request.data.get('status') # Expecting 'approved' or 'rejected'
        note = request.data.get('note', '')

        if not rebate_id or not new_status:
            return Response({"error": "rebate_id and status are required."}, status=status.HTTP_400_BAD_REQUEST)

        valid_statuses = ['approved', 'rejected', 'pending']
        if new_status not in valid_statuses:
            return Response({"error": f"Invalid status. Must be one of {valid_statuses}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rebate = RebateApp.objects.get(id=rebate_id)
            rebate.status = new_status
            rebate.save()

            # Create notification for the student
            status_text = new_status.capitalize()
            Notification.objects.create(
                user=rebate.user,
                title=f"Rebate Application {status_text}",
                content=f"Your rebate application for the period {rebate.start_date} to {rebate.end_date} has been {new_status}. {f'Note: {note}' if note else ''}",
                category='unseen'
            )

            return Response({
                "message": f"Rebate status updated to {new_status}",
                "status": new_status
            }, status=status.HTTP_200_OK)

        except RebateApp.DoesNotExist:
            return Response({"error": "Rebate application not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

class AdminFeedbackStatusUpdateView(APIView):
    """
    Admin-only: Update a feedback's status.
    Also sends a notification to the user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        feedback_id = request.data.get('id')
        new_status = request.data.get('status')  # 'pending', 'in_progress', 'resolved'

        if not feedback_id or not new_status:
            return Response({"error": "id and status are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            feedback = Feedback.objects.get(id=feedback_id)
        except Feedback.DoesNotExist:
            return Response({"error": "Feedback not found."}, status=status.HTTP_404_NOT_FOUND)

        # Ensure valid status
        valid_statuses = dict(Feedback.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response({"error": f"Invalid status. Must be one of {list(valid_statuses)}."}, status=status.HTTP_400_BAD_REQUEST)

        feedback.status = new_status
        feedback.save()

        # Send notification to student
        status_display = dict(Feedback.STATUS_CHOICES).get(new_status, new_status.capitalize())
        
        notif_title = f"Feedback Status Updated: {feedback.category}"
        notif_content = f"The status of your feedback regarding '{feedback.category}' has been updated to {status_display}."

        Notification.objects.create(
            user=feedback.user,
            title=notif_title,
            content=notif_content,
            category='unseen'
        )

        return Response({
            "message": f"Feedback #{feedback.id} status updated to {status_display}",
            "status": new_status
        }, status=status.HTTP_200_OK)


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
    Groups bookings by their shared QR code so one QR = one entry with all items.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from collections import OrderedDict
        from decimal import Decimal

        bookings = (
            MyBooking.objects
            .filter(user=request.user)
            .select_related('booking__item', 'qr_code')
            .order_by('-booked_at')
        )

        # Group by QR code
        grouped = OrderedDict()
        for mb in bookings:
            qr_key = mb.qr_code.code if mb.qr_code else f"legacy-{mb.pk}"

            if qr_key not in grouped:
                grouped[qr_key] = {
                    "qr_code_id": qr_key,
                    "booked_at": mb.booked_at,
                    "status": mb.status,
                    "items": [],
                    "total_cost": Decimal("0.00"),
                }

            item = mb.booking.item
            item_total = mb.quantity * item.cost
            grouped[qr_key]["items"].append({
                "id": mb.id,
                "item_name": item.name,
                "item_cost": float(item.cost),
                "quantity": mb.quantity,
                "month": item.month,
            })
            grouped[qr_key]["total_cost"] += item_total

            # If any item in the group is not-scanned, the whole group is not-scanned
            if mb.status == 'confirmed-not-scanned':
                grouped[qr_key]["status"] = 'confirmed-not-scanned'

        result = []
        for data in grouped.values():
            data["total_cost"] = float(data["total_cost"])
            result.append(data)

        return Response(result, status=status.HTTP_200_OK)


class BookingListView(APIView):
    """
    API View to return a list of available bookings.
    Filters out bookings with 0 available count.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        hall_id = request.query_params.get('hall_id')
        
        # Only show bookings where available_count > 0
        bookings = Booking.objects.filter(available_count__gt=0).select_related('item', 'hall').order_by('day_and_time')
        
        if hall_id:
            bookings = bookings.filter(hall_id=hall_id)
        elif getattr(request.user, 'hall_of_residence', None):
            bookings = bookings.filter(hall=request.user.hall_of_residence)
            
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartAddView(APIView):
    """
    API View to add an item to the cart or update its quantity.
    Expected payload: {"item_id": 1, "quantity": 2}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity', 1)
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                return Response({"error": "Quantity must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"error": "Invalid quantity."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            item = Item.objects.get(id=item_id)
        except Item.DoesNotExist:
            return Response({"error": "Item not found."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve user's hall
        user_hall = getattr(request.user, 'hall_of_residence', None)
        
        # Check available booking for this item
        bookings = Booking.objects.filter(item=item)
        if user_hall:
            hall_bookings = bookings.filter(hall=user_hall)
            if hall_bookings.exists():
                bookings = hall_bookings
        
        booking = bookings.order_by('day_and_time').first()
        if not booking:
            return Response({"error": "Item is not currently available for booking."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate new total quantity
        cart_item = Cart.objects.filter(user=request.user, item=item).first()
        current_quantity = cart_item.quantity if cart_item else 0
        new_quantity = current_quantity + quantity
        
        if new_quantity > booking.available_count:
            return Response({
                "error": "Limit reached",
                "message": f"Cannot add more. Only {booking.available_count} available, and you already have {current_quantity} in cart."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not cart_item:
            # We create a new cart item if it doesn't exist
            cart_item = Cart.objects.create(user=request.user, item=item, quantity=quantity)
        else:
            # Otherwise we update the quantity of the existing one
            cart_item.quantity = new_quantity
            cart_item.save()
            
        return Response({
            "message": "Item added to cart.", 
            "cart_item_id": cart_item.id, 
            "quantity": cart_item.quantity
        }, status=status.HTTP_200_OK)


class CartDeleteView(APIView):
    """
    API View to delete an item from the cart.
    Expected payload: {"item_id": 1}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        item_id = request.data.get('item_id')
        try:
            cart_item = Cart.objects.get(user=request.user, item_id=item_id)
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                return Response({"message": "Quantity decreased.", "quantity": cart_item.quantity}, status=status.HTTP_200_OK)
            else:
                cart_item.delete()
                return Response({"message": "Item removed from cart."}, status=status.HTTP_200_OK)
        except Cart.DoesNotExist:
            return Response({"error": "Item not in cart."}, status=status.HTTP_404_NOT_FOUND)


class CartCheckView(APIView):
    """
    API View to check all cart items against Booking availability.
    Adjusts cart item quantities if they exceed Booking available_count or if Booking doesn't exist.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart_items = Cart.objects.filter(user=request.user)
        user_hall = request.user.hall_of_residence
        changes_made = []

        for cart_item in cart_items:
            bookings = Booking.objects.filter(item=cart_item.item)
            if user_hall:
                hall_bookings = bookings.filter(hall=user_hall)
                if hall_bookings.exists():
                    bookings = hall_bookings
            
            booking = bookings.order_by('day_and_time').first()
            
            if not booking:
                changes_made.append({
                    "item": cart_item.item.name, 
                    "message": "Item not available. Removed from cart."
                })
                cart_item.delete()
                continue
                
            if cart_item.quantity > booking.available_count:
                if booking.available_count == 0:
                    changes_made.append({
                        "item": cart_item.item.name, 
                        "message": "Item out of stock. Removed from cart."
                    })
                    cart_item.delete()
                else:
                    changes_made.append({
                        "item": cart_item.item.name, 
                        "message": f"Only {booking.available_count} available. Reduced from {cart_item.quantity} to {booking.available_count}."
                    })
                    cart_item.quantity = booking.available_count
                    cart_item.save()

        updated_cart = Cart.objects.filter(user=request.user)
        serializer = CartSerializer(updated_cart, many=True)
        return Response({
            "cart": serializer.data,
            "changes": changes_made
        }, status=status.HTTP_200_OK)


class CartCheckoutView(APIView):
    """
    API View to confirm booking from cart.
    Deducts available_count from Booking and creates MyBooking records.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        user_hall = request.user.hall_of_residence
        checkout_data = []

        from django.db import transaction
        import uuid

        with transaction.atomic():
            # Generate ONE QR code for the entire checkout session
            unique_qr = f"QR-{uuid.uuid4().hex[:12].upper()}"
            qr_entry = QRDatabase.objects.create(
                user=request.user,
                code=unique_qr
            )

            for cart_item in cart_items:
                # Lock the relevant bookings to prevent concurrent overselling
                bookings = Booking.objects.select_for_update().filter(item=cart_item.item)
                if user_hall:
                    hall_bookings = bookings.filter(hall=user_hall)
                    if hall_bookings.exists():
                        bookings = hall_bookings
                
                booking = bookings.filter(available_count__gte=cart_item.quantity).order_by('day_and_time').first()

                if not booking:
                    booking = bookings.order_by('day_and_time').first()
                    if not booking or booking.available_count < cart_item.quantity:
                        return Response({
                            "error": f"Insufficient availability for {cart_item.item.name}. Please check cart again."
                        }, status=status.HTTP_400_BAD_REQUEST)

                booking.available_count -= cart_item.quantity
                booking.save()

                my_booking = MyBooking.objects.create(
                    user=request.user,
                    booking=booking,
                    qr_code=qr_entry,
                    quantity=cart_item.quantity,
                    status='confirmed-not-scanned'
                )

                checkout_data.append({
                    "item": cart_item.item.name,
                    "quantity": cart_item.quantity,
                    "booking_id": my_booking.id,
                })

            cart_items.delete()

        return Response({
            "message": "Checkout successful. Bookings confirmed.", 
            "qr_code": unique_qr,
            "details": checkout_data
        }, status=status.HTTP_200_OK)


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
        import calendar
        from datetime import date
        user = request.user
        target_month = request.query_params.get('month')
        
        fixed_charges_qs = FixedCharges.objects.filter(user=user)
        total_fixed_charges = fixed_charges_qs.aggregate(total=Sum('bill'))['total'] or 0
        fixed_charges_list = list(fixed_charges_qs.values('hall__name', 'category', 'bill'))

        bookings = MyBooking.objects.filter(user=user, status__icontains='confirmed').select_related('booking__item')

        # Filter by the actual booking date (booked_at) rather than item.month string
        # This avoids mismatches when item.month is 'Error' or has different casing
        if target_month:
            try:
                month_num = list(calendar.month_name).index(target_month)  # 1-12
                current_year = date.today().year
                bookings = bookings.filter(
                    booked_at__year=current_year,
                    booked_at__month=month_num
                )
            except (ValueError, IndexError):
                pass
            
        bills_by_month = {}
        
        for mb in bookings:
            item = mb.booking.item
            # Use the item's declared month if available, else derive from booked_at
            month = item.month if (item.month and item.month != 'Error') else (
                mb.booked_at.strftime("%B") if mb.booked_at else target_month or 'Unknown'
            )
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

            # Include payment status for student
            pay_status_obj = BillPaymentStatus.objects.filter(user=user, month=month).first()
            payment_status = pay_status_obj.status if pay_status_obj else 'unpaid'
            paid_on = pay_status_obj.paid_on.isoformat() if pay_status_obj and pay_status_obj.paid_on else None

            response_data.append({
                "month": month,
                "total_item_cost": data["total_item_cost"],
                "total_fixed_charges": total_fixed_charges,
                "rebate_days": rebate_days,
                "daily_refund_rate": daily_refund_rate,
                "rebate_refund": rebate_refund,
                "total_bill": total_bill,
                "fixed_charges_details": fixed_charges_list,
                "items_bought": data["items"],
                "payment_status": payment_status,
                "paid_on": paid_on,
            })
            
        return Response(response_data, status=status.HTTP_200_OK)


class AdminBillingView(APIView):
    """
    Admin-only API View to return billing data for ALL students.
    Used by the AdminBillingPage frontend.
    """
    permission_classes = [IsAuthenticated]

    def _get_rebate_days_for_month(self, user, month_str):
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
            user=user, status='approved',
            start_date__lte=month_end, end_date__gte=month_start
        )

        total_days = 0
        for rebate in approved_rebates:
            overlap_start = max(rebate.start_date, month_start)
            overlap_end = min(rebate.end_date, month_end)
            total_days += (overlap_end - overlap_start).days + 1

        return total_days

    def get(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        target_month = request.query_params.get('month')

        from .models import CustomUser
        students = CustomUser.objects.filter(role='student').select_related('hall_of_residence')

        # Get daily refund rate for the target month
        daily_refund_rate = 0
        if target_month:
            daily_refund_obj = DailyRebateRefund.objects.filter(month=target_month).first()
            daily_refund_rate = float(daily_refund_obj.cost) if daily_refund_obj else 0

        import calendar
        from datetime import date
        total_days_in_month = 0
        if target_month:
            try:
                year = date.today().year
                month_num = list(calendar.month_name).index(target_month)
                total_days_in_month = calendar.monthrange(year, month_num)[1]
            except (ValueError, IndexError):
                total_days_in_month = 30

        result = []
        for student in students:
            # Fixed charges
            fixed_qs = FixedCharges.objects.filter(user=student)
            total_fixed = fixed_qs.aggregate(total=Sum('bill'))['total'] or 0

            # Extras (MyBooking items)
            bookings_qs = MyBooking.objects.filter(
                user=student, status__icontains='confirmed'
            ).select_related('booking__item')
            if target_month:
                try:
                    import calendar as cal
                    month_num = list(cal.month_name).index(target_month)
                    bookings_qs = bookings_qs.filter(
                        booked_at__year=date.today().year,
                        booked_at__month=month_num
                    )
                except (ValueError, IndexError):
                    pass

            extras = []
            total_extras = 0
            for mb in bookings_qs:
                item = mb.booking.item
                cost = float(mb.quantity * item.cost)
                extras.append({
                    "item_name": item.name,
                    "quantity": mb.quantity,
                    "cost_per_item": float(item.cost),
                    "total_cost": cost,
                    "date": mb.booked_at.strftime("%Y-%m-%d") if mb.booked_at else "",
                    "hall": item.hall.name if item.hall else "",
                })
                total_extras += cost

            # Rebate
            rebate_days = 0
            if target_month:
                rebate_days = self._get_rebate_days_for_month(student, target_month)

            rebate_refund = rebate_days * daily_refund_rate
            basic_bill = float(total_fixed)
            grand_total = basic_bill + total_extras - rebate_refund

            # Payment status
            pay_status_obj = BillPaymentStatus.objects.filter(user=student, month=target_month).first() if target_month else None
            pay_status = pay_status_obj.status.capitalize() if pay_status_obj else "Unpaid"
            paid_on = pay_status_obj.paid_on.isoformat() if pay_status_obj and pay_status_obj.paid_on else None

            result.append({
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "roll_no": student.roll_no,
                "hall": student.hall_of_residence.name if student.hall_of_residence else "N/A",
                "rebate_days": rebate_days,
                "daily_refund_rate": daily_refund_rate,
                "rebate_refund": rebate_refund,
                "fixed_charges": float(total_fixed),
                "extras": extras,
                "total_extras": total_extras,
                "basic_bill": basic_bill,
                "grand_total": grand_total,
                "total_days_in_month": total_days_in_month,
                "payStatus": pay_status,
                "paid_on": paid_on,
            })

        return Response(result, status=status.HTTP_200_OK)


class AdminBillStatusUpdateView(APIView):
    """
    Admin-only: Update a student's bill payment status for a given month.
    Also sends a notification to the student.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        month = request.data.get('month')
        new_status = request.data.get('status')  # 'paid', 'unpaid', 'overdue', 'waived'

        if not user_id or not month or not new_status:
            return Response({"error": "user_id, month, and status are required."}, status=status.HTTP_400_BAD_REQUEST)

        from .models import CustomUser
        try:
            student = CustomUser.objects.get(id=user_id, role='student')
        except CustomUser.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        from django.utils import timezone
        obj, created = BillPaymentStatus.objects.update_or_create(
            user=student,
            month=month,
            defaults={
                'status': new_status.lower(),
                'paid_on': timezone.now() if new_status.lower() == 'paid' else None
            }
        )

        # Send notification to student
        status_display = new_status.capitalize()
        if new_status.lower() == 'paid':
            notif_title = f"{month} Bill Paid"
            notif_content = f"Your {month} mess bill has been marked as paid by the admin."
        elif new_status.lower() == 'overdue':
            notif_title = f"{month} Bill Overdue"
            notif_content = f"Your {month} mess bill is overdue. Please settle the payment at the earliest."
        elif new_status.lower() == 'waived':
            notif_title = f"{month} Bill Waived"
            notif_content = f"Your {month} mess bill has been waived by the admin."
        else:
            notif_title = f"{month} Bill Status Updated"
            notif_content = f"Your {month} mess bill status has been updated to {status_display}."

        # Append optional admin note
        note = request.data.get('note')
        if note:
            notif_content += f"\n\nNote from admin: {note}"

        Notification.objects.create(
            user=student,
            title=notif_title,
            content=notif_content,
            category='unseen'
        )

        return Response({
            "message": f"Bill status updated to {status_display} for {student.name}",
            "payStatus": status_display,
            "paid_on": obj.paid_on.isoformat() if obj.paid_on else None
        }, status=status.HTTP_200_OK)


class AdminSendReminderView(APIView):
    """
    Admin-only: Send a bill payment reminder notification to a student.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        month = request.data.get('month')
        note = request.data.get('note')

        if not user_id or not month:
            return Response({"error": "user_id and month are required."}, status=status.HTTP_400_BAD_REQUEST)

        from .models import CustomUser
        try:
            student = CustomUser.objects.get(id=user_id, role='student')
        except CustomUser.DoesNotExist:
            return Response({"error": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

        Notification.objects.create(
            user=student,
            title=f"{month} Bill Reminder",
            content=note if note else f"Reminder: Please pay your {month} mess bill at the earliest. Contact the mess office for more details.",
            category='unseen'
        )

        return Response({
            "message": f"Reminder sent to {student.name} for {month}"
        }, status=status.HTTP_200_OK)


class MessBillPDFView(APIView):
    """
    API View to generate and download a PDF mess bill for the authenticated user.
    Uses ReportLab to render the PDF in-memory with a unique verification UUID.
    """
    permission_classes = [IsAuthenticated]

    def _get_rebate_days_for_month(self, user, month_str):
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
            user=user, status='approved',
            start_date__lte=month_end, end_date__gte=month_start
        )
        total_days = 0
        for rebate in approved_rebates:
            overlap_start = max(rebate.start_date, month_start)
            overlap_end = min(rebate.end_date, month_end)
            total_days += (overlap_end - overlap_start).days + 1
        return total_days

    def get(self, request):
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from datetime import date

        user = request.user
        target_month = request.query_params.get('month')

        if not target_month:
            return Response({"error": "month query parameter is required (e.g. ?month=March)"},
                            status=status.HTTP_400_BAD_REQUEST)

        # ── Gather bill data ──
        fixed_charges_qs = FixedCharges.objects.filter(user=user)
        total_fixed_charges = fixed_charges_qs.aggregate(total=Sum('bill'))['total'] or 0
        fixed_charges_list = list(fixed_charges_qs.values('category', 'bill'))

        bookings = MyBooking.objects.filter(
            user=user, status__icontains='confirmed',
            booking__item__month=target_month
        ).select_related('booking__item')

        items_data = []
        total_item_cost = 0
        for mb in bookings:
            item = mb.booking.item
            cost = mb.quantity * item.cost
            items_data.append({
                "name": item.name,
                "qty": mb.quantity,
                "unit_cost": float(item.cost),
                "total": float(cost),
            })
            total_item_cost += float(cost)

        rebate_days = self._get_rebate_days_for_month(user, target_month)
        daily_refund_obj = DailyRebateRefund.objects.filter(month=target_month).first()
        daily_refund_rate = float(daily_refund_obj.cost) if daily_refund_obj else 0
        rebate_refund = rebate_days * daily_refund_rate

        total_bill = total_item_cost + float(total_fixed_charges) - rebate_refund

        # ── Generate verification UUID ──
        verification_id = uuid.uuid4()
        BillVerification.objects.create(
            user=user,
            month=target_month,
            verification_id=verification_id,
            is_generated=True,
        )

        # ── Build PDF in memory ──
        buffer = io.BytesIO()
        width, height = A4
        c = canvas.Canvas(buffer, pagesize=A4)

        # --- Header ---
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width / 2, height - 40, "CMMS - Mess Bill Statement")
        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2, height - 56, "Indian Institute of Technology Kanpur")

        # Divider
        c.setLineWidth(0.8)
        c.line(40, height - 68, width - 40, height - 68)

        # --- Student Info ---
        y = height - 95
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, "Student Details")
        y -= 20
        c.setFont("Helvetica", 10)
        info_lines = [
            f"Name:        {user.name}",
            f"Roll No:     {user.roll_no}",
            f"Hall:        {user.hall_of_residence.name if user.hall_of_residence else 'N/A'}",
            f"Month:       {target_month} {date.today().year}",
        ]
        for line in info_lines:
            c.drawString(50, y, line)
            y -= 16

        # Divider
        y -= 6
        c.line(40, y, width - 40, y)
        y -= 20

        # --- Itemized Charges Table ---
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, "Itemized Charges")
        y -= 20

        # Table header
        c.setFont("Helvetica-Bold", 9)
        c.drawString(50, y, "Item")
        c.drawString(250, y, "Qty")
        c.drawString(320, y, "Unit Cost")
        c.drawRightString(width - 50, y, "Total")
        y -= 4
        c.setLineWidth(0.4)
        c.line(50, y, width - 50, y)
        y -= 14

        c.setFont("Helvetica", 9)
        if items_data:
            for item in items_data:
                c.drawString(50, y, str(item["name"]))
                c.drawString(260, y, str(item["qty"]))
                c.drawString(320, y, f"Rs. {item['unit_cost']:.2f}")
                c.drawRightString(width - 50, y, f"Rs. {item['total']:.2f}")
                y -= 16
                if y < 100:
                    c.showPage()
                    y = height - 50
        else:
            c.drawString(50, y, "No items booked for this month.")
            y -= 16

        # Subtotal line
        y -= 4
        c.line(50, y, width - 50, y)
        y -= 16
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Subtotal (Items)")
        c.drawRightString(width - 50, y, f"Rs. {total_item_cost:.2f}")
        y -= 24

        # --- Fixed Charges ---
        c.setFont("Helvetica-Bold", 11)
        c.drawString(40, y, "Fixed Charges")
        y -= 18
        c.setFont("Helvetica", 9)
        if fixed_charges_list:
            for fc in fixed_charges_list:
                c.drawString(50, y, str(fc["category"]))
                c.drawRightString(width - 50, y, f"Rs. {float(fc['bill']):.2f}")
                y -= 16
        else:
            c.drawString(50, y, "No fixed charges.")
            y -= 16

        c.line(50, y, width - 50, y)
        y -= 16
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Subtotal (Fixed)")
        c.drawRightString(width - 50, y, f"Rs. {float(total_fixed_charges):.2f}")
        y -= 24

        # --- Rebate ---
        if rebate_refund > 0:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(40, y, "Rebate Deduction")
            y -= 18
            c.setFont("Helvetica", 9)
            c.drawString(50, y, f"Approved rebate days: {rebate_days}  x  Rs. {daily_refund_rate:.2f}/day")
            c.drawRightString(width - 50, y, f"- Rs. {rebate_refund:.2f}")
            y -= 24

        # --- Grand Total ---
        c.setLineWidth(1.2)
        c.line(40, y, width - 40, y)
        y -= 22
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Total Payable")
        c.drawRightString(width - 50, y, f"Rs. {total_bill:.2f}")
        y -= 30
        c.line(40, y, width - 40, y)

        # --- Verification Footer ---
        y -= 30
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, y, f"Verification ID: {verification_id}")
        y -= 14
        c.drawCentredString(width / 2, y, "This is a system-generated document. For verification, contact the Mess Administration.")

        # ── Finalize ──
        c.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="MessBill_{target_month}.pdf"'
        return response


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


class CustomTokenRefreshView(APIView):
    """
    API View to refresh an access token using the HttpOnly refresh_token cookie.
    If valid, it sets a new access_token cookie.
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response({"error": "No refresh token provided"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)

            response = Response({"message": "Token refreshed successfully"}, status=status.HTTP_200_OK)

            response.set_cookie(
                key=settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'),
                value=new_access_token,
                expires=settings.SIMPLE_JWT.get('ACCESS_TOKEN_LIFETIME', 0),
                secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
                httponly=True,
                samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
            )

            # If token rotation is enabled, simplejwt might also give a new refresh token.
            # Usually simple jwt refresh endpoint takes care of this via its own view. 
            # Doing it manually if needed:
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS", False):
                new_refresh_token = str(refresh)
                response.set_cookie(
                    key="refresh_token",
                    value=new_refresh_token,
                    expires=settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME', 0),
                    secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', False),
                    httponly=True,
                    samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax')
                )

            return response
        except Exception as e:
            return Response({"error": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)



class LogoutView(APIView):
    def post(self, request):
        response = Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie(settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'))
        response.delete_cookie("refresh_token")
        return response


class DailyRebateRefundListView(APIView):
    """
    API View to list and create/update Daily Rebate Refunds.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rebates = DailyRebateRefund.objects.all().order_by('month')
        serializer = DailyRebateRefundSerializer(rebates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        month = request.data.get('month')
        cost = request.data.get('cost')
        
        if not month or cost is None:
            return Response({"error": "Month and cost are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        rebate_obj, created = DailyRebateRefund.objects.update_or_create(
            month=month,
            defaults={'cost': cost}
        )
        
        serializer = DailyRebateRefundSerializer(rebate_obj)
        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.data, status=status.HTTP_200_OK)


class FixedChargesListView(APIView):
    """
    API View to list Fixed Charges.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') == 'admin':
            charges = FixedCharges.objects.all().order_by('hall', 'category')
        else:
            charges = FixedCharges.objects.filter(user=request.user).order_by('hall', 'category')
        
        serializer = FixedChargesSerializer(charges, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = FixedChargesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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


# ──────────────────────────────────────────────
# Admin Extras Management Views
# ──────────────────────────────────────────────

class AdminExtrasDashboardView(APIView):
    """
    Admin-only: Get all hall menus and recent orders for Extras Management.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        # 1. Get Menus (Items with Bookings)
        halls = Hall.objects.all()
        menus = {hall.name: [] for hall in halls}
        
        items = Item.objects.select_related('hall').all()
        
        # Pre-fetch bookings to get stock
        bookings = Booking.objects.all()
        booking_map = {}
        for b in bookings:
            if b.item_id not in booking_map:
                booking_map[b.item_id] = b
            else:
                if b.day_and_time < booking_map[b.item_id].day_and_time:
                     booking_map[b.item_id] = b
        
        # Pre-fetch sold count using status='confirmed-not-scanned' or 'confirmed-scanned' -> any confirmed
        from django.db.models import Sum
        my_bookings = MyBooking.objects.filter(status__startswith='confirmed').values('booking__item_id').annotate(total_sold=Sum('quantity'))
        sold_map = {mb['booking__item_id']: mb['total_sold'] for mb in my_bookings}

        for item in items:
            booking = booking_map.get(item.id)
            stock = booking.available_count if booking else 0
            sold = sold_map.get(item.id, 0)
            
            menus[item.hall.name].append({
                "id": item.id,
                "name": item.name,
                "price": float(item.cost),
                "stock": stock,
                "sold": sold
            })

        # 2. Get Live Order Feed
        orders = []
        recent_bookings = MyBooking.objects.filter(status__startswith='confirmed').select_related('user', 'booking__item', 'booking__hall').order_by('-booked_at')[:50]
        for mb in recent_bookings:
            orders.append({
                "id": str(mb.id),
                "student": mb.user.name,
                "hall": mb.booking.hall.name if mb.booking.hall else "",
                "item": mb.booking.item.name,
                "price": float(mb.booking.item.cost),
                "time": mb.booked_at.strftime("%I:%M %p") if mb.booked_at else "",
                "token": mb.qr_code.code[:12] if mb.qr_code else "N/A"  # shorter token for display
            })

        return Response({
            "menus": menus,
            "orders": orders
        }, status=status.HTTP_200_OK)


class AdminExtrasItemView(APIView):
    """
    Admin-only: Add, edit, or delete an extra Item.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
            
        name = request.data.get('name')
        price = request.data.get('price')
        stock = request.data.get('stock')
        hall_name = request.data.get('hallName')

        try:
            hall = Hall.objects.get(name=hall_name)
        except Hall.DoesNotExist:
            return Response({"error": "Hall not found"}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        current_month = list(calendar.month_name)[now.month]

        item = Item.objects.create(name=name, cost=price, hall=hall, month=current_month)
        Booking.objects.create(item=item, hall=hall, available_count=stock, day_and_time=timezone.now())

        return Response({"message": "Item created"}, status=status.HTTP_201_CREATED)

    def put(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
            
        item_id = request.data.get('id')
        name = request.data.get('name')
        price = request.data.get('price')
        stock = request.data.get('stock')

        try:
            item = Item.objects.get(id=item_id)
            if name: item.name = name
            if price is not None: item.cost = price
            item.save()

            if stock is not None:
                # Update all bookings for this item, or the first one
                booking = Booking.objects.filter(item=item).first()
                if booking:
                    booking.available_count = stock
                    booking.save()
                else:
                    from django.utils import timezone
                    Booking.objects.create(item=item, hall=item.hall, available_count=stock, day_and_time=timezone.now())

            return Response({"message": "Item updated"}, status=status.HTTP_200_OK)
        except Item.DoesNotExist:
            return Response({"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)
            
        item_id = request.data.get('id')
        try:
            item = Item.objects.get(id=item_id)
            item.delete()  # Cascade deletes bookings
            return Response({"message": "Item deleted"}, status=status.HTTP_200_OK)
        except Item.DoesNotExist:
            return Response({"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND)


class AdminSendNotificationView(APIView):
    """Admin-only: Send custom notifications to a student or multiple students."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        payload = AdminNotificationPayload(
            title=request.data.get('title', '').strip(),
            content=request.data.get('content', '').strip(),
            all_students=request.data.get('all_students', False),
            user_ids=request.data.get('user_ids', []),
            emails=request.data.get('emails', []),
            roll_nos=request.data.get('roll_nos', []),
        )

        if not payload.title or not payload.content:
            return Response({"error": "Title and content are required."}, status=status.HTTP_400_BAD_REQUEST)

        from .models import CustomUser

        targets = CustomUser.objects.filter(role='student')

        if not payload.all_students:
            if payload.user_ids and not isinstance(payload.user_ids, list):
                return Response({"error": "user_ids must be a list."}, status=status.HTTP_400_BAD_REQUEST)
            if payload.emails and isinstance(payload.emails, str):
                payload.emails = [email.strip() for email in payload.emails.split(',') if email.strip()]
            if payload.roll_nos and isinstance(payload.roll_nos, str):
                payload.roll_nos = [roll.strip() for roll in payload.roll_nos.split(',') if roll.strip()]

            if payload.emails and not isinstance(payload.emails, list):
                return Response({"error": "emails must be a list or comma-separated string."}, status=status.HTTP_400_BAD_REQUEST)
            if payload.roll_nos and not isinstance(payload.roll_nos, list):
                return Response({"error": "roll_nos must be a list or comma-separated string."}, status=status.HTTP_400_BAD_REQUEST)

            if not (payload.user_ids or payload.emails or payload.roll_nos):
                return Response({"error": "Must provide all_students:true or at least one of user_ids / emails / roll_nos."}, status=status.HTTP_400_BAD_REQUEST)

            q = CustomUser.objects.filter(role='student')
            if payload.user_ids:
                q = q.filter(id__in=payload.user_ids)
            if payload.emails:
                q = q.filter(email__in=payload.emails)
            if payload.roll_nos:
                q = q.filter(roll_no__in=payload.roll_nos)

            targets = q

        created = 0
        for student in targets.distinct():
            Notification.objects.create(
                user=student,
                title=payload.title,
                content=payload.content,
                category='unseen'
            )
            created += 1

        if created == 0:
            return Response({"error": "No matching student recipients found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "message": f"Notification sent to {created} student(s).",
            "sent_count": created
        }, status=status.HTTP_200_OK)

class AdminStudentListView(APIView):
    """Admin-only: Get student list for targeted notifications."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        from .models import CustomUser
        students = CustomUser.objects.filter(role='student').order_by('name')
        serializer = UserProfileSerializer(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@dataclass
class AdminNotificationPayload:
    title: str
    content: str
    all_students: bool = False
    user_ids: list = None
    emails: list = None
    roll_nos: list = None


class AdminSendNotificationView(APIView):
    """Admin-only: Send custom notifications to a student or multiple students."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        payload = AdminNotificationPayload(
            title=request.data.get('title', '').strip(),
            content=request.data.get('content', '').strip(),
            all_students=request.data.get('all_students', False),
            user_ids=request.data.get('user_ids', []),
            emails=request.data.get('emails', []),
            roll_nos=request.data.get('roll_nos', []),
        )

        if not payload.title or not payload.content:
            return Response({"error": "Title and content are required."}, status=status.HTTP_400_BAD_REQUEST)

        from .models import CustomUser

        targets = CustomUser.objects.filter(role='student')

        if not payload.all_students:
            if payload.user_ids and not isinstance(payload.user_ids, list):
                return Response({"error": "user_ids must be a list."}, status=status.HTTP_400_BAD_REQUEST)
            if payload.emails and isinstance(payload.emails, str):
                payload.emails = [email.strip() for email in payload.emails.split(',') if email.strip()]
            if payload.roll_nos and isinstance(payload.roll_nos, str):
                payload.roll_nos = [roll.strip() for roll in payload.roll_nos.split(',') if roll.strip()]

            if payload.emails and not isinstance(payload.emails, list):
                return Response({"error": "emails must be a list or comma-separated string."}, status=status.HTTP_400_BAD_REQUEST)
            if payload.roll_nos and not isinstance(payload.roll_nos, list):
                return Response({"error": "roll_nos must be a list or comma-separated string."}, status=status.HTTP_400_BAD_REQUEST)

            if not (payload.user_ids or payload.emails or payload.roll_nos):
                return Response({"error": "Must provide all_students:true or at least one of user_ids / emails / roll_nos."}, status=status.HTTP_400_BAD_REQUEST)

            q = CustomUser.objects.filter(role='student')
            if payload.user_ids:
                q = q.filter(id__in=payload.user_ids)
            if payload.emails:
                q = q.filter(email__in=payload.emails)
            if payload.roll_nos:
                q = q.filter(roll_no__in=payload.roll_nos)

            targets = q

        created = 0
        for student in targets.distinct():
            Notification.objects.create(
                user=student,
                title=payload.title,
                content=payload.content,
                category='unseen'
            )
            created += 1

        if created == 0:
            return Response({"error": "No matching student recipients found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "message": f"Notification sent to {created} student(s).",
            "sent_count": created
        }, status=status.HTTP_200_OK)


class AdminQRScanView(APIView):
    """
    Admin-only: Scan a QR code to mark all associated bookings as 'confirmed-scanned'.
    Expected payload: {"qr_code": "QR-XXXXXXXXXXXX"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        qr_code = request.data.get('qr_code', '').strip()
        if not qr_code:
            return Response({"error": "qr_code is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            qr_entry = QRDatabase.objects.get(code=qr_code)
        except QRDatabase.DoesNotExist:
            return Response({"error": "Invalid QR code. No matching record found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all bookings linked to this QR
        my_bookings = (
            MyBooking.objects
            .filter(qr_code=qr_entry)
            .select_related('booking__item', 'booking__hall', 'user')
        )

        if not my_bookings.exists():
            return Response({"error": "No bookings found for this QR code."}, status=status.HTTP_404_NOT_FOUND)

        # Check if already scanned
        unscanned = my_bookings.filter(status='confirmed-not-scanned')
        already_scanned = not unscanned.exists()

        if already_scanned:
            # Still return details, but inform that it's already scanned
            first = my_bookings.first()
            items = []
            for mb in my_bookings:
                items.append({
                    "item_name": mb.booking.item.name,
                    "quantity": mb.quantity,
                    "cost": float(mb.booking.item.cost * mb.quantity),
                    "hall": mb.booking.hall.name if mb.booking.hall else "",
                })
            return Response({
                "status": "already_scanned",
                "message": "This QR code has already been scanned.",
                "student": {
                    "name": first.user.name,
                    "email": first.user.email,
                    "roll_no": first.user.roll_no,
                },
                "items": items,
                "scanned_at": first.booked_at,
            }, status=status.HTTP_200_OK)

        # Mark all unscanned bookings as scanned
        scanned_count = unscanned.update(status='confirmed-scanned')

        first = my_bookings.first()
        items = []
        total_cost = 0
        for mb in my_bookings:
            item_cost = float(mb.booking.item.cost * mb.quantity)
            items.append({
                "item_name": mb.booking.item.name,
                "quantity": mb.quantity,
                "cost": item_cost,
                "hall": mb.booking.hall.name if mb.booking.hall else "",
            })
            total_cost += item_cost

        # Send notification to the student
        Notification.objects.create(
            user=first.user,
            title="Order Collected",
            content=f"Your order ({scanned_count} item(s), ₹{total_cost:.0f}) has been collected at the mess counter.",
            category='unseen'
        )

        return Response({
            "status": "success",
            "message": f"QR code scanned successfully. {scanned_count} item(s) marked as collected.",
            "student": {
                "name": first.user.name,
                "email": first.user.email,
                "roll_no": first.user.roll_no,
            },
            "items": items,
            "total_cost": total_cost,
        }, status=status.HTTP_200_OK)
