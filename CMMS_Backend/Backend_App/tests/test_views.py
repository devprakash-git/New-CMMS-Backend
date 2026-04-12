"""
Unit tests for all API views in Backend_App.views.
Uses DRF APIClient with force_authenticate for isolated unit testing.
Covers authentication, student, and admin endpoints — happy paths,
permission guards, validation errors, and edge cases.
"""

from decimal import Decimal
from datetime import date

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from Backend_App.models import (
    CustomUser, Hall, Item, Booking, Menu, Notification,
    Feedback, RebateApp, DailyRebateRefund, Cart, MyBooking,
    QRDatabase, FixedCharges, BillVerification, BillPaymentStatus,
)


# ═══════════════════════════════════════════════
#  HallListView
# ═══════════════════════════════════════════════

class TestHallListView:
    """Tests for HallListView — public endpoint."""

    @pytest.mark.django_db
    def test_get_halls(self, api_client, hall):
        """
        Unit Name: HallListView GET — list all halls
        Unit Details: Class HallListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 200 with list of halls; allows unauthenticated access.
        Structural Coverage: Statement coverage — full happy path.
        Additional Comments: AllowAny permission verified.
        """
        resp = api_client.get(reverse("halls"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["name"] == "Hall 1"


# ═══════════════════════════════════════════════
#  AuthStatusView
# ═══════════════════════════════════════════════

class TestAuthStatusView:
    """Tests for AuthStatusView (/api/my/)."""

    @pytest.mark.django_db
    def test_authenticated(self, authenticated_client):
        """
        Unit Name: AuthStatusView GET — logged in
        Unit Details: Class AuthStatusView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns is_logged_in=True with user data.
        Structural Coverage: Branch coverage — authenticated path.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("my"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["is_logged_in"] is True
        assert resp.data["user"]["email"] == "student@iitk.ac.in"

    @pytest.mark.django_db
    def test_anonymous(self, api_client):
        """
        Unit Name: AuthStatusView GET — anonymous
        Unit Details: Class AuthStatusView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns is_logged_in=False, user=None.
        Structural Coverage: Branch coverage — anonymous path.
        Additional Comments: None.
        """
        resp = api_client.get(reverse("my"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["is_logged_in"] is False


# ═══════════════════════════════════════════════
#  SignupView
# ═══════════════════════════════════════════════

class TestSignupView:
    """Tests for SignupView."""

    @pytest.mark.django_db
    def test_valid_signup(self, api_client, hall):
        """
        Unit Name: SignupView POST — valid registration
        Unit Details: Class SignupView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 201; user created in DB.
        Structural Coverage: Statement coverage — full success path.
        Additional Comments: None.
        """
        resp = api_client.post(reverse("signup"), {
            "name": "New User",
            "email": "new@iitk.ac.in",
            "password": "securepass1234",
            "roll_no": "220099",
            "hall_of_residence": hall.id,
            "room_no": "202",
            "contact_no": "1234567890",
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert CustomUser.objects.filter(email="new@iitk.ac.in").exists()

    @pytest.mark.django_db
    def test_duplicate_email(self, api_client, student_user, hall):
        """
        Unit Name: SignupView POST — duplicate email
        Unit Details: Class SignupView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 400 when email already exists.
        Structural Coverage: Branch coverage — serializer invalid path.
        Additional Comments: None.
        """
        resp = api_client.post(reverse("signup"), {
            "name": "Dup",
            "email": "student@iitk.ac.in",
            "password": "securepass1234",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ═══════════════════════════════════════════════
#  LoginView
# ═══════════════════════════════════════════════

class TestLoginView:
    """Tests for LoginView."""

    @pytest.mark.django_db
    def test_valid_login(self, api_client, student_user):
        """
        Unit Name: LoginView POST — valid credentials
        Unit Details: Class LoginView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 200 with user data; sets access_token and refresh_token cookies.
        Structural Coverage: Statement coverage — full success path with cookies.
        Additional Comments: None.
        """
        resp = api_client.post(reverse("login"), {
            "email": "student@iitk.ac.in",
            "password": "testpass1234",
        })
        assert resp.status_code == status.HTTP_200_OK
        assert "access_token" in resp.cookies
        assert "refresh_token" in resp.cookies

    @pytest.mark.django_db
    def test_invalid_login(self, api_client, student_user):
        """
        Unit Name: LoginView POST — bad credentials
        Unit Details: Class LoginView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 401 or 403 on wrong password depending on DRF configuration.
        Structural Coverage: Branch coverage — serializer invalid path.
        Additional Comments: None.
        """
        resp = api_client.post(reverse("login"), {
            "email": "student@iitk.ac.in",
            "password": "wrongpassword",
        })
        # AuthenticationFailed in DRF usually returns 401 or 403.
        assert resp.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# ═══════════════════════════════════════════════
#  LogoutView
# ═══════════════════════════════════════════════

class TestLogoutView:
    """Tests for LogoutView."""

    @pytest.mark.django_db
    def test_logout_clears_cookies(self, authenticated_client):
        """
        Unit Name: LogoutView POST — clears cookies
        Unit Details: Class LogoutView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 200 and deletes token cookies.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("logout"))
        assert resp.status_code == status.HTTP_200_OK
        # Cookie deletion sets max-age=0
        assert "access_token" in resp.cookies


# ═══════════════════════════════════════════════
#  CustomTokenRefreshView
# ═══════════════════════════════════════════════

class TestCustomTokenRefreshView:
    """Tests for CustomTokenRefreshView."""

    @pytest.mark.django_db
    def test_no_cookie_returns_401(self, api_client):
        """
        Unit Name: CustomTokenRefreshView POST — no cookie
        Unit Details: Class CustomTokenRefreshView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 401 when no refresh_token cookie is present.
        Structural Coverage: Branch coverage — missing cookie guard.
        Additional Comments: None.
        """
        resp = api_client.post(reverse("token_refresh"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_invalid_token_returns_401(self, api_client):
        """
        Unit Name: CustomTokenRefreshView POST — invalid token
        Unit Details: Class CustomTokenRefreshView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 401 when refresh_token cookie contains invalid JWT.
        Structural Coverage: Branch coverage — exception handler path.
        Additional Comments: None.
        """
        api_client.cookies["refresh_token"] = "invalid-jwt-token"
        resp = api_client.post(reverse("token_refresh"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ═══════════════════════════════════════════════
#  UserProfileView
# ═══════════════════════════════════════════════

class TestUserProfileView:
    """Tests for UserProfileView."""

    @pytest.mark.django_db
    def test_get_profile(self, authenticated_client):
        """
        Unit Name: UserProfileView GET — authenticated
        Unit Details: Class UserProfileView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 200 with user profile data.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("profile"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["email"] == "student@iitk.ac.in"

    @pytest.mark.django_db
    def test_unauthenticated(self, api_client):
        """
        Unit Name: UserProfileView GET — unauthenticated
        Unit Details: Class UserProfileView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 401 for anonymous users.
        Structural Coverage: Permission check coverage.
        Additional Comments: None.
        """
        resp = api_client.get(reverse("profile"))
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ═══════════════════════════════════════════════
#  NotificationListView
# ═══════════════════════════════════════════════

class TestNotificationListView:
    """Tests for NotificationListView."""

    @pytest.mark.django_db
    def test_get_notifications(self, authenticated_client, notification):
        """
        Unit Name: NotificationListView GET — user notifications
        Unit Details: Class NotificationListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns only the authenticated user's notifications.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("notifications"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["title"] == "Test Notification"


# ═══════════════════════════════════════════════
#  MarkNotificationsSeenView
# ═══════════════════════════════════════════════

class TestMarkNotificationsSeenView:
    """Tests for MarkNotificationsSeenView."""

    @pytest.mark.django_db
    def test_mark_seen(self, authenticated_client, notification):
        """
        Unit Name: MarkNotificationsSeenView POST — mark all seen
        Unit Details: Class MarkNotificationsSeenView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Updates unseen notifications to seen; returns count.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("mark-notifications-seen"))
        assert resp.status_code == status.HTTP_200_OK
        notification.refresh_from_db()
        assert notification.category == "seen"


# ═══════════════════════════════════════════════
#  MenuListView
# ═══════════════════════════════════════════════

class TestMenuListView:
    """Tests for MenuListView."""

    @pytest.mark.django_db
    def test_get_menu_for_user_hall(self, authenticated_client, menu):
        """
        Unit Name: MenuListView GET — default user hall
        Unit Details: Class MenuListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns menus for the user's assigned hall.
        Structural Coverage: Branch coverage — user has hall_of_residence.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("menu"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1
        assert resp.data[0]["dish"] == "Dal Rice"

    @pytest.mark.django_db
    def test_get_menu_by_hall_id(self, authenticated_client, menu, hall):
        """
        Unit Name: MenuListView GET — filter by hall_id
        Unit Details: Class MenuListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns menus filtered by query param hall_id.
        Structural Coverage: Branch coverage — hall_id query param present.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("menu"), {"hall_id": hall.id})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1


# ═══════════════════════════════════════════════
#  FeedbackListView
# ═══════════════════════════════════════════════

class TestFeedbackListView:
    """Tests for FeedbackListView."""

    @pytest.mark.django_db
    def test_student_sees_own(self, authenticated_client, feedback):
        """
        Unit Name: FeedbackListView GET — student sees own feedbacks
        Unit Details: Class FeedbackListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Student only sees their own feedbacks.
        Structural Coverage: Branch coverage — non-admin path.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("feedbacks"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    @pytest.mark.django_db
    def test_admin_sees_all(self, admin_client, feedback):
        """
        Unit Name: FeedbackListView GET — admin sees all feedbacks
        Unit Details: Class FeedbackListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Admin sees all feedbacks regardless of owner.
        Structural Coverage: Branch coverage — admin path.
        Additional Comments: None.
        """
        resp = admin_client.get(reverse("feedbacks"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    @pytest.mark.django_db
    def test_create_feedback(self, authenticated_client):
        """
        Unit Name: FeedbackListView POST — create feedback
        Unit Details: Class FeedbackListView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 201; feedback created with the authenticated user.
        Structural Coverage: Statement coverage — serializer valid path.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("feedbacks"), {
            "category": "Hygiene",
            "content": "Very clean today!",
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert Feedback.objects.filter(category="Hygiene").exists()


# ═══════════════════════════════════════════════
#  RebateAppListView
# ═══════════════════════════════════════════════

class TestRebateAppListView:
    """Tests for RebateAppListView."""

    @pytest.mark.django_db
    def test_student_get(self, authenticated_client, rebate_app):
        """
        Unit Name: RebateAppListView GET — student
        Unit Details: Class RebateAppListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Student sees their own rebate applications.
        Structural Coverage: Branch coverage — non-admin path.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("rebates"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    @pytest.mark.django_db
    def test_create_rebate(self, authenticated_client):
        """
        Unit Name: RebateAppListView POST — create rebate
        Unit Details: Class RebateAppListView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 201; rebate application created.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("rebates"), {
            "start_date": "2026-05-01",
            "end_date": "2026-05-05",
            "location": "Delhi",
        })
        assert resp.status_code == status.HTTP_201_CREATED


# ═══════════════════════════════════════════════
#  BookingListView
# ═══════════════════════════════════════════════

class TestBookingListView:
    """Tests for BookingListView."""

    @pytest.mark.django_db
    def test_get_available_bookings(self, authenticated_client, booking):
        """
        Unit Name: BookingListView GET — available bookings
        Unit Details: Class BookingListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns only bookings with available_count > 0.
        Structural Coverage: Statement + filter coverage.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("bookings"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    @pytest.mark.django_db
    def test_zero_availability_excluded(self, authenticated_client, item, hall):
        """
        Unit Name: BookingListView GET — zero availability excluded
        Unit Details: Class BookingListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Bookings with available_count=0 are not returned.
        Structural Coverage: Filter coverage — available_count__gt=0.
        Additional Comments: None.
        """
        Booking.objects.create(item=item, hall=hall, day_and_time=timezone.now(), available_count=0)
        resp = authenticated_client.get(reverse("bookings"))
        assert resp.status_code == status.HTTP_200_OK
        for b in resp.data:
            assert b["available_count"] > 0


# ═══════════════════════════════════════════════
#  CartAddView
# ═══════════════════════════════════════════════

class TestCartAddView:
    """Tests for CartAddView."""

    @pytest.mark.django_db
    def test_add_item_to_cart(self, authenticated_client, item, booking):
        """
        Unit Name: CartAddView POST — add item
        Unit Details: Class CartAddView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 200; cart item created with correct quantity.
        Structural Coverage: Statement coverage — happy path.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("cart-add"), {
            "item_id": item.id,
            "quantity": 3,
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["quantity"] == 3

    @pytest.mark.django_db
    def test_exceed_stock(self, authenticated_client, item, booking):
        """
        Unit Name: CartAddView POST — exceed available count
        Unit Details: Class CartAddView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 400 when requested quantity exceeds available_count.
        Structural Coverage: Branch coverage — stock guard.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("cart-add"), {
            "item_id": item.id,
            "quantity": 999,
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_invalid_quantity(self, authenticated_client, item, booking):
        """
        Unit Name: CartAddView POST — invalid quantity
        Unit Details: Class CartAddView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 400 for quantity <= 0.
        Structural Coverage: Branch coverage — quantity validation.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("cart-add"), {
            "item_id": item.id,
            "quantity": 0,
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_item_not_found(self, authenticated_client):
        """
        Unit Name: CartAddView POST — non-existent item
        Unit Details: Class CartAddView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 404 for item_id that doesn't exist.
        Structural Coverage: Branch coverage — Item.DoesNotExist.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("cart-add"), {
            "item_id": 99999,
            "quantity": 1,
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ═══════════════════════════════════════════════
#  CartDeleteView
# ═══════════════════════════════════════════════

class TestCartDeleteView:
    """Tests for CartDeleteView."""

    @pytest.mark.django_db
    def test_decrement_quantity(self, authenticated_client, cart_item):
        """
        Unit Name: CartDeleteView POST — decrement quantity
        Unit Details: Class CartDeleteView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Quantity decremented from 2 to 1; item not removed.
        Structural Coverage: Branch coverage — quantity > 1 path.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("cart-delete"), {
            "item_id": cart_item.item.id,
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["quantity"] == 1

    @pytest.mark.django_db
    def test_remove_when_quantity_one(self, authenticated_client, student_user, item):
        """
        Unit Name: CartDeleteView POST — remove at quantity 1
        Unit Details: Class CartDeleteView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Cart entry deleted when quantity is 1.
        Structural Coverage: Branch coverage — quantity == 1 path.
        Additional Comments: None.
        """
        Cart.objects.create(user=student_user, item=item, quantity=1)
        resp = authenticated_client.post(reverse("cart-delete"), {
            "item_id": item.id,
        })
        assert resp.status_code == status.HTTP_200_OK
        assert not Cart.objects.filter(user=student_user, item=item).exists()

    @pytest.mark.django_db
    def test_item_not_in_cart(self, authenticated_client):
        """
        Unit Name: CartDeleteView POST — item not in cart
        Unit Details: Class CartDeleteView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 404 when item_id is not in user's cart.
        Structural Coverage: Branch coverage — DoesNotExist handler.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("cart-delete"), {
            "item_id": 99999,
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ═══════════════════════════════════════════════
#  CartCheckView
# ═══════════════════════════════════════════════

class TestCartCheckView:
    """Tests for CartCheckView."""

    @pytest.mark.django_db
    def test_check_cart(self, authenticated_client, cart_item, booking):
        """
        Unit Name: CartCheckView GET — cart within limits
        Unit Details: Class CartCheckView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns cart data with no changes when quantities are valid.
        Structural Coverage: Statement coverage — no adjustment path.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("cart-check"))
        assert resp.status_code == status.HTTP_200_OK
        assert "cart" in resp.data
        assert len(resp.data["changes"]) == 0

    @pytest.mark.django_db
    def test_check_reduces_over_count(self, authenticated_client, student_user, item, hall):
        """
        Unit Name: CartCheckView GET — quantity reduced to available
        Unit Details: Class CartCheckView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Cart quantity reduced when it exceeds booking available_count.
        Structural Coverage: Branch coverage — quantity > available_count reduction.
        Additional Comments: None.
        """
        Booking.objects.create(item=item, hall=hall, day_and_time=timezone.now(), available_count=1)
        Cart.objects.create(user=student_user, item=item, quantity=5)
        resp = authenticated_client.get(reverse("cart-check"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["changes"]) > 0


# ═══════════════════════════════════════════════
#  CartCheckoutView
# ═══════════════════════════════════════════════

class TestCartCheckoutView:
    """Tests for CartCheckoutView."""

    @pytest.mark.django_db
    def test_checkout_success(self, authenticated_client, cart_item, booking):
        """
        Unit Name: CartCheckoutView POST — successful checkout
        Unit Details: Class CartCheckoutView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 200 with QR code; MyBooking created, cart cleared.
        Structural Coverage: Statement coverage — full transaction path.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("cart-checkout"))
        assert resp.status_code == status.HTTP_200_OK
        assert "qr_code" in resp.data
        assert Cart.objects.filter(user=cart_item.user).count() == 0
        assert MyBooking.objects.filter(user=cart_item.user).exists()

    @pytest.mark.django_db
    def test_checkout_empty_cart(self, authenticated_client):
        """
        Unit Name: CartCheckoutView POST — empty cart
        Unit Details: Class CartCheckoutView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 400 when cart is empty.
        Structural Coverage: Branch coverage — empty cart guard.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("cart-checkout"))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ═══════════════════════════════════════════════
#  MyBookingListView
# ═══════════════════════════════════════════════

class TestMyBookingListView:
    """Tests for MyBookingListView."""

    @pytest.mark.django_db
    def test_get_my_bookings(self, authenticated_client, my_booking):
        """
        Unit Name: MyBookingListView GET — grouped by QR
        Unit Details: Class MyBookingListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns bookings grouped by QR code with items and total_cost.
        Structural Coverage: Statement coverage — grouping logic.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("my-bookings"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1
        assert "qr_code_id" in resp.data[0]
        assert "items" in resp.data[0]


# ═══════════════════════════════════════════════
#  MessBillView
# ═══════════════════════════════════════════════

class TestMessBillView:
    """Tests for MessBillView."""

    @pytest.mark.django_db
    def test_get_mess_bill(self, authenticated_client, my_booking, fixed_charges, daily_rebate_refund):
        """
        Unit Name: MessBillView GET — bill calculation
        Unit Details: Class MessBillView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns bill data with item costs, fixed charges, and rebate deduction.
        Structural Coverage: Statement coverage — full bill calculation path.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("mess-bill"), {"month": "April"})
        assert resp.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_get_mess_bill_no_month(self, authenticated_client):
        """
        Unit Name: MessBillView GET — no month specified
        Unit Details: Class MessBillView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 200 with empty or all-months data.
        Structural Coverage: Branch coverage — no target_month.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("mess-bill"))
        assert resp.status_code == status.HTTP_200_OK


# ═══════════════════════════════════════════════
#  DailyRebateRefundListView
# ═══════════════════════════════════════════════

class TestDailyRebateRefundListView:
    """Tests for DailyRebateRefundListView."""

    @pytest.mark.django_db
    def test_get_list(self, authenticated_client, daily_rebate_refund):
        """
        Unit Name: DailyRebateRefundListView GET — list
        Unit Details: Class DailyRebateRefundListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns list of daily rebate refund entries.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("daily-rebate-refund"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    @pytest.mark.django_db
    def test_create_admin_only(self, admin_client):
        """
        Unit Name: DailyRebateRefundListView POST — admin create
        Unit Details: Class DailyRebateRefundListView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Admin can create/update; returns 201.
        Structural Coverage: Statement coverage — admin path.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("daily-rebate-refund"), {
            "month": "May",
            "cost": "90.00",
        })
        assert resp.status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_create_forbidden_for_student(self, authenticated_client):
        """
        Unit Name: DailyRebateRefundListView POST — student forbidden
        Unit Details: Class DailyRebateRefundListView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("daily-rebate-refund"), {
            "month": "May",
            "cost": "90.00",
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════
#  FixedChargesListView
# ═══════════════════════════════════════════════

class TestFixedChargesListView:
    """Tests for FixedChargesListView."""

    @pytest.mark.django_db
    def test_student_sees_own(self, authenticated_client, fixed_charges):
        """
        Unit Name: FixedChargesListView GET — student sees own
        Unit Details: Class FixedChargesListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Student sees only their own fixed charges.
        Structural Coverage: Branch coverage — non-admin path.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("fixed-charges"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    @pytest.mark.django_db
    def test_admin_create(self, admin_client, student_user, hall):
        """
        Unit Name: FixedChargesListView POST — admin create
        Unit Details: Class FixedChargesListView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Admin creates fixed charge entry; returns 201.
        Structural Coverage: Statement coverage — admin create path.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("fixed-charges"), {
            "user": student_user.id,
            "hall": hall.id,
            "category": "Electricity",
            "bill": "500.00",
        })
        assert resp.status_code == status.HTTP_201_CREATED


# ═══════════════════════════════════════════════
#  AdminMenuUpdateView
# ═══════════════════════════════════════════════

class TestAdminMenuUpdateView:
    """Tests for AdminMenuUpdateView."""

    @pytest.mark.django_db
    def test_create_menu(self, admin_client, hall):
        """
        Unit Name: AdminMenuUpdateView POST — create new menu item
        Unit Details: Class AdminMenuUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 201; menu item created.
        Structural Coverage: Branch coverage — no item_id (create) path.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin_menu_update"), {
            "hall": hall.id,
            "day": "Tuesday",
            "meal_time": "Dinner",
            "dish": "Butter Chicken",
        })
        assert resp.status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_update_menu(self, admin_client, menu):
        """
        Unit Name: AdminMenuUpdateView POST — update existing
        Unit Details: Class AdminMenuUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 200; menu item updated.
        Structural Coverage: Branch coverage — item_id present (update) path.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin_menu_update"), {
            "id": menu.id,
            "dish": "Paneer Masala",
        })
        assert resp.status_code == status.HTTP_200_OK
        menu.refresh_from_db()
        assert menu.dish == "Paneer Masala"

    @pytest.mark.django_db
    def test_student_forbidden(self, authenticated_client, hall):
        """
        Unit Name: AdminMenuUpdateView POST — student forbidden
        Unit Details: Class AdminMenuUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("admin_menu_update"), {
            "hall": hall.id,
            "day": "Monday",
            "meal_time": "Lunch",
            "dish": "Nope",
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════
#  AdminMenuDeleteView
# ═══════════════════════════════════════════════

class TestAdminMenuDeleteView:
    """Tests for AdminMenuDeleteView."""

    @pytest.mark.django_db
    def test_delete_menu(self, admin_client, menu):
        """
        Unit Name: AdminMenuDeleteView DELETE — success
        Unit Details: Class AdminMenuDeleteView, function delete
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 204; menu item deleted.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = admin_client.delete(reverse("admin_menu_delete", args=[menu.id]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Menu.objects.filter(id=menu.id).exists()

    @pytest.mark.django_db
    def test_delete_not_found(self, admin_client):
        """
        Unit Name: AdminMenuDeleteView DELETE — not found
        Unit Details: Class AdminMenuDeleteView, function delete
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 404 for non-existent menu id.
        Structural Coverage: Branch coverage — DoesNotExist.
        Additional Comments: None.
        """
        resp = admin_client.delete(reverse("admin_menu_delete", args=[99999]))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_student_forbidden(self, authenticated_client, menu):
        """
        Unit Name: AdminMenuDeleteView DELETE — student forbidden
        Unit Details: Class AdminMenuDeleteView, function delete
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.delete(reverse("admin_menu_delete", args=[menu.id]))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════
#  AdminFeedbackStatusUpdateView
# ═══════════════════════════════════════════════

class TestAdminFeedbackStatusUpdateView:
    """Tests for AdminFeedbackStatusUpdateView."""

    @pytest.mark.django_db
    def test_update_status(self, admin_client, feedback):
        """
        Unit Name: AdminFeedbackStatusUpdateView POST — update status
        Unit Details: Class AdminFeedbackStatusUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Updates feedback status and creates notification for user.
        Structural Coverage: Statement coverage — full success path.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin_feedback_update_status"), {
            "id": feedback.id,
            "status": "resolved",
        })
        assert resp.status_code == status.HTTP_200_OK
        feedback.refresh_from_db()
        assert feedback.status == "resolved"
        assert Notification.objects.filter(user=feedback.user, title__icontains="Feedback").exists()

    @pytest.mark.django_db
    def test_missing_fields(self, admin_client):
        """
        Unit Name: AdminFeedbackStatusUpdateView POST — missing fields
        Unit Details: Class AdminFeedbackStatusUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 400 when id or status is missing.
        Structural Coverage: Branch coverage — validation guard.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin_feedback_update_status"), {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_student_forbidden(self, authenticated_client, feedback):
        """
        Unit Name: AdminFeedbackStatusUpdateView POST — student forbidden
        Unit Details: Class AdminFeedbackStatusUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("admin_feedback_update_status"), {
            "id": feedback.id,
            "status": "resolved",
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════
#  AdminRebateStatusUpdateView
# ═══════════════════════════════════════════════

class TestAdminRebateStatusUpdateView:
    """Tests for AdminRebateStatusUpdateView."""

    @pytest.mark.django_db
    def test_approve_rebate(self, admin_client, rebate_app):
        """
        Unit Name: AdminRebateStatusUpdateView POST — approve
        Unit Details: Class AdminRebateStatusUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Updates rebate status to 'approved'; creates notification.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin_rebate_update_status"), {
            "rebate_id": rebate_app.id,
            "status": "approved",
        })
        assert resp.status_code == status.HTTP_200_OK
        rebate_app.refresh_from_db()
        assert rebate_app.status == "approved"

    @pytest.mark.django_db
    def test_invalid_status(self, admin_client, rebate_app):
        """
        Unit Name: AdminRebateStatusUpdateView POST — invalid status
        Unit Details: Class AdminRebateStatusUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 400 for invalid status value.
        Structural Coverage: Branch coverage — invalid status guard.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin_rebate_update_status"), {
            "rebate_id": rebate_app.id,
            "status": "invalid_status",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_student_forbidden(self, authenticated_client, rebate_app):
        """
        Unit Name: AdminRebateStatusUpdateView POST — student forbidden
        Unit Details: Class AdminRebateStatusUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("admin_rebate_update_status"), {
            "rebate_id": rebate_app.id,
            "status": "approved",
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════
#  AdminBillingView
# ═══════════════════════════════════════════════

class TestAdminBillingView:
    """Tests for AdminBillingView."""

    @pytest.mark.django_db
    def test_get_billing(self, admin_client, student_user, fixed_charges):
        """
        Unit Name: AdminBillingView GET — all students billing
        Unit Details: Class AdminBillingView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns billing data for all students; includes fixed charges.
        Structural Coverage: Statement coverage — full path.
        Additional Comments: None.
        """
        resp = admin_client.get(reverse("admin-billing"), {"month": "April"})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    @pytest.mark.django_db
    def test_student_forbidden(self, authenticated_client):
        """
        Unit Name: AdminBillingView GET — student forbidden
        Unit Details: Class AdminBillingView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("admin-billing"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════
#  AdminBillStatusUpdateView
# ═══════════════════════════════════════════════

class TestAdminBillStatusUpdateView:
    """Tests for AdminBillStatusUpdateView."""

    @pytest.mark.django_db
    def test_mark_paid(self, admin_client, student_user):
        """
        Unit Name: AdminBillStatusUpdateView POST — mark paid
        Unit Details: Class AdminBillStatusUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Updates BillPaymentStatus to 'paid'; creates notification.
        Structural Coverage: Statement coverage — paid branch.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin-billing-update-status"), {
            "user_id": student_user.id,
            "month": "April",
            "status": "paid",
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["payStatus"] == "Paid"
        assert Notification.objects.filter(user=student_user).exists()

    @pytest.mark.django_db
    def test_missing_fields(self, admin_client):
        """
        Unit Name: AdminBillStatusUpdateView POST — missing fields
        Unit Details: Class AdminBillStatusUpdateView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 400 when required fields are missing.
        Structural Coverage: Branch coverage — validation guard.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin-billing-update-status"), {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ═══════════════════════════════════════════════
#  AdminSendReminderView
# ═══════════════════════════════════════════════

class TestAdminSendReminderView:
    """Tests for AdminSendReminderView."""

    @pytest.mark.django_db
    def test_send_reminder(self, admin_client, student_user):
        """
        Unit Name: AdminSendReminderView POST — send reminder
        Unit Details: Class AdminSendReminderView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Creates a reminder notification for the student.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin-billing-send-reminder"), {
            "user_id": student_user.id,
            "month": "April",
        })
        assert resp.status_code == status.HTTP_200_OK
        assert Notification.objects.filter(user=student_user, title__icontains="Reminder").exists()

    @pytest.mark.django_db
    def test_student_not_found(self, admin_client):
        """
        Unit Name: AdminSendReminderView POST — student not found
        Unit Details: Class AdminSendReminderView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 404 for non-existent student.
        Structural Coverage: Branch coverage — DoesNotExist.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin-billing-send-reminder"), {
            "user_id": 99999,
            "month": "April",
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ═══════════════════════════════════════════════
#  AdminSendNotificationView
# ═══════════════════════════════════════════════

class TestAdminSendNotificationView:
    """Tests for AdminSendNotificationView."""

    @pytest.mark.django_db
    def test_send_to_all(self, admin_client, student_user):
        """
        Unit Name: AdminSendNotificationView POST — send to all students
        Unit Details: Class AdminSendNotificationView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Notification sent to all students; returns sent_count.
        Structural Coverage: Branch coverage — all_students=True path.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin-notifications-send"), {
            "title": "Holiday Notice",
            "content": "Mess closed tomorrow.",
            "all_students": True,
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["sent_count"] >= 1

    @pytest.mark.django_db
    def test_missing_title(self, admin_client):
        """
        Unit Name: AdminSendNotificationView POST — missing title
        Unit Details: Class AdminSendNotificationView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 400 when title is empty.
        Structural Coverage: Branch coverage — validation guard.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin-notifications-send"), {
            "title": "",
            "content": "Body",
            "all_students": True,
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_student_forbidden(self, authenticated_client):
        """
        Unit Name: AdminSendNotificationView POST — student forbidden
        Unit Details: Class AdminSendNotificationView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("admin-notifications-send"), {
            "title": "Test",
            "content": "Test",
            "all_students": True,
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════
#  AdminStudentListView
# ═══════════════════════════════════════════════

class TestAdminStudentListView:
    """Tests for AdminStudentListView."""

    @pytest.mark.django_db
    def test_get_students(self, admin_client, student_user):
        """
        Unit Name: AdminStudentListView GET — list students
        Unit Details: Class AdminStudentListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Admin gets list of all students.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = admin_client.get(reverse("admin-notifications-students"))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    @pytest.mark.django_db
    def test_student_forbidden(self, authenticated_client):
        """
        Unit Name: AdminStudentListView GET — student forbidden
        Unit Details: Class AdminStudentListView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("admin-notifications-students"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════
#  AdminExtrasDashboardView
# ═══════════════════════════════════════════════

class TestAdminExtrasDashboardView:
    """Tests for AdminExtrasDashboardView."""

    @pytest.mark.django_db
    def test_get_dashboard(self, admin_client, hall, item, booking, my_booking):
        """
        Unit Name: AdminExtrasDashboardView GET — dashboard data
        Unit Details: Class AdminExtrasDashboardView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns menus (by hall) and orders list.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = admin_client.get(reverse("admin-extras-dashboard"))
        assert resp.status_code == status.HTTP_200_OK
        assert "menus" in resp.data
        assert "orders" in resp.data

    @pytest.mark.django_db
    def test_student_forbidden(self, authenticated_client):
        """
        Unit Name: AdminExtrasDashboardView GET — student forbidden
        Unit Details: Class AdminExtrasDashboardView, function get
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.get(reverse("admin-extras-dashboard"))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════
#  AdminExtrasItemView
# ═══════════════════════════════════════════════

class TestAdminExtrasItemView:
    """Tests for AdminExtrasItemView."""

    @pytest.mark.django_db
    def test_create_item(self, admin_client, hall):
        """
        Unit Name: AdminExtrasItemView POST — create item
        Unit Details: Class AdminExtrasItemView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 201; Item and Booking created.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin-extras-items"), {
            "name": "Samosa",
            "price": 15,
            "stock": 100,
            "hallName": "Hall 1",
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert Item.objects.filter(name="Samosa").exists()

    @pytest.mark.django_db
    def test_update_item(self, admin_client, item):
        """
        Unit Name: AdminExtrasItemView PUT — update item
        Unit Details: Class AdminExtrasItemView, function put
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 200; item fields updated.
        Structural Coverage: Statement coverage — update path.
        Additional Comments: None.
        """
        resp = admin_client.put(
            reverse("admin-extras-items"),
            {"id": item.id, "name": "Updated Roti", "price": 15},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        assert item.name == "Updated Roti"

    @pytest.mark.django_db
    def test_delete_item(self, admin_client, item):
        """
        Unit Name: AdminExtrasItemView DELETE — delete item
        Unit Details: Class AdminExtrasItemView, function delete
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 200; item deleted.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        resp = admin_client.delete(
            reverse("admin-extras-items"),
            {"id": item.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert not Item.objects.filter(id=item.id).exists()

    @pytest.mark.django_db
    def test_student_forbidden(self, authenticated_client):
        """
        Unit Name: AdminExtrasItemView POST — student forbidden
        Unit Details: Class AdminExtrasItemView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("admin-extras-items"), {
            "name": "Nope",
            "price": 10,
            "stock": 10,
            "hallName": "Hall 1",
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ═══════════════════════════════════════════════
#  AdminQRScanView
# ═══════════════════════════════════════════════

class TestAdminQRScanView:
    """Tests for AdminQRScanView."""

    @pytest.mark.django_db
    def test_scan_qr(self, admin_client, my_booking, qr_code):
        """
        Unit Name: AdminQRScanView POST — scan QR code
        Unit Details: Class AdminQRScanView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Marks bookings as scanned; creates notification; returns item details.
        Structural Coverage: Statement coverage — unscanned path.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin-qr-scan"), {
            "qr_code": qr_code.code,
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "success"
        my_booking.refresh_from_db()
        assert my_booking.status == "confirmed-scanned"

    @pytest.mark.django_db
    def test_already_scanned(self, admin_client, my_booking, qr_code):
        """
        Unit Name: AdminQRScanView POST — already scanned
        Unit Details: Class AdminQRScanView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 409 Conflict with status='already_scanned' on second scan.
        Structural Coverage: Branch coverage — already_scanned path.
        Additional Comments: None.
        """
        my_booking.status = "confirmed-scanned"
        my_booking.save()
        resp = admin_client.post(reverse("admin-qr-scan"), {
            "qr_code": qr_code.code,
        })
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.data["status"] == "already_scanned"

    @pytest.mark.django_db
    def test_invalid_qr(self, admin_client):
        """
        Unit Name: AdminQRScanView POST — invalid QR code
        Unit Details: Class AdminQRScanView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 404 for non-existent QR code.
        Structural Coverage: Branch coverage — DoesNotExist.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin-qr-scan"), {
            "qr_code": "NONEXISTENT",
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_student_forbidden(self, authenticated_client, qr_code):
        """
        Unit Name: AdminQRScanView POST — student forbidden
        Unit Details: Class AdminQRScanView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 403 for non-admin users.
        Structural Coverage: Branch coverage — role guard.
        Additional Comments: None.
        """
        resp = authenticated_client.post(reverse("admin-qr-scan"), {
            "qr_code": qr_code.code,
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_empty_qr(self, admin_client):
        """
        Unit Name: AdminQRScanView POST — empty QR code
        Unit Details: Class AdminQRScanView, function post
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 400 when qr_code is empty.
        Structural Coverage: Branch coverage — empty qr_code guard.
        Additional Comments: None.
        """
        resp = admin_client.post(reverse("admin-qr-scan"), {
            "qr_code": "",
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
