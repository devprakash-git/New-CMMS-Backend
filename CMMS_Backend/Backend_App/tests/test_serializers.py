"""
Unit tests for all serializers in Backend_App.serializers.
Covers validation logic, output fields, nested serializer fields,
and read-only field enforcement.
"""

from decimal import Decimal
from datetime import date

import pytest
from django.test import RequestFactory
from rest_framework.exceptions import AuthenticationFailed

from Backend_App.models import (
    CustomUser, Hall, Item, Booking, Menu, Feedback, RebateApp,
    Cart, MyBooking, QRDatabase, DailyRebateRefund, FixedCharges, Notification,
)
from Backend_App.serializers import (
    HallSerializer,
    UserProfileSerializer,
    NotificationSerializer,
    MenuSerializer,
    FeedbackSerializer,
    RebateAppSerializer,
    SignupSerializer,
    LoginSerializer,
    ResetPasswordEmailSerializer,
    ResetPasswordSerializer,
    MyBookingSerializer,
    BookingSerializer,
    CartSerializer,
    DailyRebateRefundSerializer,
    FixedChargesSerializer,
)


# ═══════════════════════════════════════════════
#  HallSerializer
# ═══════════════════════════════════════════════

class TestHallSerializer:
    """Tests for HallSerializer."""

    @pytest.mark.django_db
    def test_output_fields(self, hall):
        """
        Unit Name: HallSerializer output fields
        Unit Details: Class HallSerializer
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Serialized data contains 'id' and 'name' keys with correct values.
        Structural Coverage: Statement coverage — serializer instantiation and .data access.
        Additional Comments: None.
        """
        data = HallSerializer(hall).data
        assert set(data.keys()) == {"id", "name"}
        assert data["name"] == "Hall 1"


# ═══════════════════════════════════════════════
#  UserProfileSerializer
# ═══════════════════════════════════════════════

class TestUserProfileSerializer:
    """Tests for UserProfileSerializer."""

    @pytest.mark.django_db
    def test_output_fields(self, student_user):
        """
        Unit Name: UserProfileSerializer output fields
        Unit Details: Class UserProfileSerializer
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Output includes all expected fields; hall_of_residence resolves to hall name.
        Structural Coverage: Statement coverage including nested source field.
        Additional Comments: None.
        """
        data = UserProfileSerializer(student_user).data
        assert data["email"] == "student@iitk.ac.in"
        assert data["name"] == "Test Student"
        assert data["hall_of_residence"] == "Hall 1"
        assert data["role"] == "student"

    @pytest.mark.django_db
    def test_no_hall(self, admin_user):
        """
        Unit Name: UserProfileSerializer — user with no hall
        Unit Details: Class UserProfileSerializer, field hall_of_residence
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: hall_of_residence is None or omitted when user has no assigned hall.
        Structural Coverage: Branch coverage — null FK path.
        Additional Comments: None.
        """
        data = UserProfileSerializer(admin_user).data
        # DRF may omit a dotted source field if the relation is None
        assert data.get("hall_of_residence") is None


# ═══════════════════════════════════════════════
#  NotificationSerializer
# ═══════════════════════════════════════════════

class TestNotificationSerializer:
    """Tests for NotificationSerializer."""

    @pytest.mark.django_db
    def test_output_fields(self, notification):
        """
        Unit Name: NotificationSerializer output fields
        Unit Details: Class NotificationSerializer
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Output contains id, title, content, category, time.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        data = NotificationSerializer(notification).data
        assert set(data.keys()) == {"id", "title", "content", "category", "time"}
        assert data["title"] == "Test Notification"
        assert data["category"] == "unseen"


# ═══════════════════════════════════════════════
#  MenuSerializer
# ═══════════════════════════════════════════════

class TestMenuSerializer:
    """Tests for MenuSerializer."""

    @pytest.mark.django_db
    def test_output_includes_hall_name(self, menu):
        """
        Unit Name: MenuSerializer output fields
        Unit Details: Class MenuSerializer, field hall_name (source='hall.name')
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Output includes 'hall_name' resolved from related Hall.
        Structural Coverage: Statement coverage including nested source.
        Additional Comments: None.
        """
        data = MenuSerializer(menu).data
        assert data["hall_name"] == "Hall 1"
        assert data["dish"] == "Dal Rice"
        assert "category" in data


# ═══════════════════════════════════════════════
#  FeedbackSerializer
# ═══════════════════════════════════════════════

class TestFeedbackSerializer:
    """Tests for FeedbackSerializer."""

    @pytest.mark.django_db
    def test_output_fields(self, feedback):
        """
        Unit Name: FeedbackSerializer output fields
        Unit Details: Class FeedbackSerializer
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Output includes user_name, user_email, status, content.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        data = FeedbackSerializer(feedback).data
        assert data["user_name"] == "Test Student"
        assert data["user_email"] == "student@iitk.ac.in"
        assert data["status"] == "pending"

    @pytest.mark.django_db
    def test_read_only_fields(self):
        """
        Unit Name: FeedbackSerializer read-only enforcement
        Unit Details: Class FeedbackSerializer, Meta read_only_fields
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: id, user, date, status are not writable via serializer input.
        Structural Coverage: Statement coverage — read_only enforcement verified.
        Additional Comments: None.
        """
        ser = FeedbackSerializer(data={
            "category": "Cleanliness",
            "content": "Tables are dirty."
        })
        assert ser.is_valid(), ser.errors
        # read_only fields should not be in validated_data
        assert "id" not in ser.validated_data
        assert "user" not in ser.validated_data
        assert "status" not in ser.validated_data


# ═══════════════════════════════════════════════
#  RebateAppSerializer
# ═══════════════════════════════════════════════

class TestRebateAppSerializer:
    """Tests for RebateAppSerializer."""

    @pytest.mark.django_db
    def test_output_fields(self, rebate_app):
        """
        Unit Name: RebateAppSerializer output fields
        Unit Details: Class RebateAppSerializer
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Output includes user_name, user_email, dates, location, status.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        data = RebateAppSerializer(rebate_app).data
        assert data["user_name"] == "Test Student"
        assert data["status"] == "pending"
        assert data["location"] == "Home"

    @pytest.mark.django_db
    def test_read_only_fields(self):
        """
        Unit Name: RebateAppSerializer read-only enforcement
        Unit Details: Class RebateAppSerializer, Meta read_only_fields
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: id, user, created_at, status are read-only.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        ser = RebateAppSerializer(data={
            "start_date": "2026-04-05",
            "end_date": "2026-04-10",
            "location": "Home",
        })
        assert ser.is_valid(), ser.errors
        assert "user" not in ser.validated_data
        assert "status" not in ser.validated_data


# ═══════════════════════════════════════════════
#  SignupSerializer
# ═══════════════════════════════════════════════

class TestSignupSerializer:
    """Tests for SignupSerializer."""

    @pytest.mark.django_db
    def test_valid_signup(self, hall):
        """
        Unit Name: SignupSerializer — valid data
        Unit Details: Class SignupSerializer, functions validate_email, create
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Serializer is valid and creates user with hashed password.
        Structural Coverage: Statement coverage — happy path through validate_email and create.
        Additional Comments: None.
        """
        data = {
            "name": "New User",
            "email": "new@iitk.ac.in",
            "password": "securepass1234",
            "roll_no": "220099",
            "hall_of_residence": hall.id,
            "room_no": "202",
            "contact_no": "1234567890",
            "role": "student",
        }
        ser = SignupSerializer(data=data)
        assert ser.is_valid(), ser.errors
        user = ser.save()
        assert user.pk is not None
        assert user.check_password("securepass1234")

    @pytest.mark.django_db
    def test_invalid_email_domain(self):
        """
        Unit Name: SignupSerializer — invalid email domain
        Unit Details: Class SignupSerializer, function validate_email
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Rejects emails not ending with @iitk.ac.in.
        Structural Coverage: Branch coverage — email validation guard.
        Additional Comments: None.
        """
        data = {
            "name": "Bad Email",
            "email": "user@gmail.com",
            "password": "securepass1234",
            "roll_no": "123456",
            "room_no": "101",
            "contact_no": "9876543210",
        }
        ser = SignupSerializer(data=data)
        assert not ser.is_valid()
        assert "email" in ser.errors

    @pytest.mark.django_db
    def test_password_too_short(self):
        """
        Unit Name: SignupSerializer — short password
        Unit Details: Class SignupSerializer, field password (min_length=8)
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Rejects passwords shorter than 8 characters.
        Structural Coverage: Statement coverage — min_length constraint.
        Additional Comments: None.
        """
        data = {
            "name": "Short Pass",
            "email": "sp@iitk.ac.in",
            "password": "abc",
            "roll_no": "123456",
            "room_no": "101",
            "contact_no": "9876543210",
        }
        ser = SignupSerializer(data=data)
        assert not ser.is_valid()
        assert "password" in ser.errors


# ═══════════════════════════════════════════════
#  LoginSerializer
# ═══════════════════════════════════════════════

class TestLoginSerializer:
    """Tests for LoginSerializer."""

    @pytest.mark.django_db
    def test_valid_login(self, student_user):
        """
        Unit Name: LoginSerializer — valid credentials
        Unit Details: Class LoginSerializer, function validate
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns access and refresh tokens plus user info.
        Structural Coverage: Statement coverage — authenticate + token generation.
        Additional Comments: Uses RequestFactory for context.
        """
        factory = RequestFactory()
        request = factory.post("/api/login/")
        ser = LoginSerializer(
            data={"email": "student@iitk.ac.in", "password": "testpass1234"},
            context={"request": request},
        )
        assert ser.is_valid(), ser.errors
        data = ser.validated_data
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["email"] == "student@iitk.ac.in"

    @pytest.mark.django_db
    def test_invalid_credentials(self, student_user):
        """
        Unit Name: LoginSerializer — wrong password
        Unit Details: Class LoginSerializer, function validate
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Raises AuthenticationFailed with invalid password.
        Structural Coverage: Branch coverage — authentication failure path.
        Additional Comments: None.
        """
        factory = RequestFactory()
        request = factory.post("/api/login/")
        ser = LoginSerializer(
            data={"email": "student@iitk.ac.in", "password": "wrongpass"},
            context={"request": request},
        )
        with pytest.raises(AuthenticationFailed):
            ser.is_valid(raise_exception=True)

    @pytest.mark.django_db
    def test_role_mismatch(self, student_user):
        """
        Unit Name: LoginSerializer — role mismatch
        Unit Details: Class LoginSerializer, function validate
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Raises AuthenticationFailed when requested role doesn't match user's role.
        Structural Coverage: Branch coverage — role check.
        Additional Comments: None.
        """
        factory = RequestFactory()
        request = factory.post("/api/login/")
        ser = LoginSerializer(
            data={"email": "student@iitk.ac.in", "password": "testpass1234", "role": "admin"},
            context={"request": request},
        )
        with pytest.raises(AuthenticationFailed, match="correct login portal"):
            ser.is_valid(raise_exception=True)


# ═══════════════════════════════════════════════
#  ResetPasswordEmailSerializer
# ═══════════════════════════════════════════════

class TestResetPasswordEmailSerializer:
    """Tests for ResetPasswordEmailSerializer."""

    @pytest.mark.django_db
    def test_valid_email(self, student_user):
        """
        Unit Name: ResetPasswordEmailSerializer — existing email
        Unit Details: Class ResetPasswordEmailSerializer, function validate_email
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Valid when email exists in the system.
        Structural Coverage: Statement coverage — exists() returns True.
        Additional Comments: None.
        """
        ser = ResetPasswordEmailSerializer(data={"email": "student@iitk.ac.in"})
        assert ser.is_valid()

    @pytest.mark.django_db
    def test_nonexistent_email(self):
        """
        Unit Name: ResetPasswordEmailSerializer — non-existent email
        Unit Details: Class ResetPasswordEmailSerializer, function validate_email
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Invalid when email does not exist.
        Structural Coverage: Branch coverage — exists() returns False.
        Additional Comments: None.
        """
        ser = ResetPasswordEmailSerializer(data={"email": "nobody@iitk.ac.in"})
        assert not ser.is_valid()
        assert "email" in ser.errors


# ═══════════════════════════════════════════════
#  ResetPasswordSerializer
# ═══════════════════════════════════════════════

class TestResetPasswordSerializer:
    """Tests for ResetPasswordSerializer."""

    def test_matching_passwords(self):
        """
        Unit Name: ResetPasswordSerializer — matching passwords
        Unit Details: Class ResetPasswordSerializer, function validate
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Valid when both password fields match.
        Structural Coverage: Statement coverage — match branch.
        Additional Comments: None.
        """
        ser = ResetPasswordSerializer(data={
            "new_password": "newsecurepass1234",
            "confirm_password": "newsecurepass1234",
        })
        assert ser.is_valid()

    def test_mismatched_passwords(self):
        """
        Unit Name: ResetPasswordSerializer — mismatched passwords
        Unit Details: Class ResetPasswordSerializer, function validate
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Invalid when passwords differ.
        Structural Coverage: Branch coverage — mismatch guard.
        Additional Comments: None.
        """
        ser = ResetPasswordSerializer(data={
            "new_password": "password1234",
            "confirm_password": "different1234",
        })
        assert not ser.is_valid()


# ═══════════════════════════════════════════════
#  BookingSerializer
# ═══════════════════════════════════════════════

class TestBookingSerializer:
    """Tests for BookingSerializer."""

    @pytest.mark.django_db
    def test_output_fields(self, booking):
        """
        Unit Name: BookingSerializer output fields
        Unit Details: Class BookingSerializer
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Output includes item_name, item_cost, hall_name, available_count.
        Structural Coverage: Statement coverage including nested source fields.
        Additional Comments: None.
        """
        data = BookingSerializer(booking).data
        assert data["item_name"] == "Extra Roti"
        assert Decimal(str(data["item_cost"])) == Decimal("10.00")
        assert data["hall_name"] == "Hall 1"
        assert data["available_count"] == 50


# ═══════════════════════════════════════════════
#  CartSerializer
# ═══════════════════════════════════════════════

class TestCartSerializer:
    """Tests for CartSerializer."""

    @pytest.mark.django_db
    def test_output_fields(self, cart_item, booking):
        """
        Unit Name: CartSerializer output fields & available_count
        Unit Details: Class CartSerializer, function get_available_count
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Includes item_name, item_cost, quantity, and computed available_count.
        Structural Coverage: Statement + method coverage — get_available_count executed.
        Additional Comments: Booking fixture provides the available_count value.
        """
        data = CartSerializer(cart_item).data
        assert data["item_name"] == "Extra Roti"
        assert data["quantity"] == 2
        assert data["available_count"] == 50


# ═══════════════════════════════════════════════
#  MyBookingSerializer
# ═══════════════════════════════════════════════

class TestMyBookingSerializer:
    """Tests for MyBookingSerializer."""

    @pytest.mark.django_db
    def test_output_fields(self, my_booking):
        """
        Unit Name: MyBookingSerializer output fields
        Unit Details: Class MyBookingSerializer
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Output includes item_name, item_cost, month, qr_code_id, status.
        Structural Coverage: Statement coverage including nested sources.
        Additional Comments: None.
        """
        data = MyBookingSerializer(my_booking).data
        assert data["item_name"] == "Extra Roti"
        assert data["qr_code_id"] == "QR-TEST123456"
        assert data["status"] == "confirmed-not-scanned"
        assert data["quantity"] == 2


# ═══════════════════════════════════════════════
#  DailyRebateRefundSerializer
# ═══════════════════════════════════════════════

class TestDailyRebateRefundSerializer:
    """Tests for DailyRebateRefundSerializer."""

    @pytest.mark.django_db
    def test_output_fields(self, daily_rebate_refund):
        """
        Unit Name: DailyRebateRefundSerializer output fields
        Unit Details: Class DailyRebateRefundSerializer
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Output contains id, month, cost.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        data = DailyRebateRefundSerializer(daily_rebate_refund).data
        assert set(data.keys()) == {"id", "month", "cost"}
        assert data["month"] == "April"


# ═══════════════════════════════════════════════
#  FixedChargesSerializer
# ═══════════════════════════════════════════════

class TestFixedChargesSerializer:
    """Tests for FixedChargesSerializer."""

    @pytest.mark.django_db
    def test_output_fields(self, fixed_charges):
        """
        Unit Name: FixedChargesSerializer output fields
        Unit Details: Class FixedChargesSerializer
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Output includes hall_name, user_email, category, bill.
        Structural Coverage: Statement coverage including nested source fields.
        Additional Comments: None.
        """
        data = FixedChargesSerializer(fixed_charges).data
        assert data["hall_name"] == "Hall 1"
        assert data["user_email"] == "student@iitk.ac.in"
        assert data["category"] == "Mess Basic"
        assert Decimal(str(data["bill"])) == Decimal("3000.00")
