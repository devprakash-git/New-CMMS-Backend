"""
Unit tests for all models in Backend_App.models.
Covers creation, field defaults, constraints, __str__ representations,
and manager methods for all 15 models.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from Backend_App.models import (
    CustomUser, Hall, Item, RebateApp, DailyRebateRefund,
    Feedback, Cart, Booking, MyBooking, QRDatabase, Menu,
    Notification, FixedCharges, BillVerification, BillPaymentStatus,
    current_month_name, get_cart_expiry,
)


# ═══════════════════════════════════════════════
#  Helper functions
# ═══════════════════════════════════════════════

class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_current_month_name(self):
        """
        Unit Name: current_month_name helper
        Unit Details: Function current_month_name()
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns the current month as a capitalized string (e.g. 'April').
        Structural Coverage: Statement coverage — single execution path.
        Additional Comments: Used as default for Item.month and DailyRebateRefund.month.
        """
        result = current_month_name()
        assert isinstance(result, str)
        assert result == date.today().strftime("%B")

    def test_get_cart_expiry(self):
        """
        Unit Name: get_cart_expiry helper
        Unit Details: Function get_cart_expiry()
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns a datetime ~7 days in the future.
        Structural Coverage: Statement coverage — single execution path.
        Additional Comments: None.
        """
        before = timezone.now() + timedelta(days=7) - timedelta(seconds=5)
        result = get_cart_expiry()
        after = timezone.now() + timedelta(days=7) + timedelta(seconds=5)
        assert before <= result <= after


# ═══════════════════════════════════════════════
#  CustomUserManager
# ═══════════════════════════════════════════════

class TestCustomUserManager:
    """Tests for the CustomUserManager create methods."""

    @pytest.mark.django_db
    def test_create_user_success(self):
        """
        Unit Name: Create user — happy path
        Unit Details: Class CustomUserManager, function create_user
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: User is created with hashed password, default role 'student', active.
        Structural Coverage: Statement coverage — all lines in create_user executed.
        Additional Comments: Verifies password is hashed (not stored plaintext).
        """
        user = CustomUser.objects.create_user(
            email="u1@iitk.ac.in", name="User One", password="securepass123"
        )
        assert user.pk is not None
        assert user.email == "u1@iitk.ac.in"
        assert user.check_password("securepass123")
        assert user.role == "student"
        assert user.is_active is True
        assert user.is_staff is False

    @pytest.mark.django_db
    def test_create_user_no_email_raises(self):
        """
        Unit Name: Create user — missing email
        Unit Details: Class CustomUserManager, function create_user
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Raises ValueError when email is empty.
        Structural Coverage: Branch coverage — email-empty guard.
        Additional Comments: None.
        """
        with pytest.raises(ValueError, match="Email"):
            CustomUser.objects.create_user(email="", name="No Email", password="pass1234")

    @pytest.mark.django_db
    def test_create_superuser_defaults(self):
        """
        Unit Name: Create superuser — default flags
        Unit Details: Class CustomUserManager, function create_superuser
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Superuser is created with is_staff=True, is_superuser=True, role='admin'.
        Structural Coverage: Statement + branch coverage — default-setting branches taken.
        Additional Comments: None.
        """
        su = CustomUser.objects.create_superuser(
            email="su@iitk.ac.in", name="Super User", password="superpass123"
        )
        assert su.is_staff is True
        assert su.is_superuser is True
        assert su.role == "admin"

    @pytest.mark.django_db
    def test_create_superuser_not_staff_raises(self):
        """
        Unit Name: Create superuser — is_staff=False rejected
        Unit Details: Class CustomUserManager, function create_superuser
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Raises ValueError when is_staff is explicitly False.
        Structural Coverage: Branch coverage — is_staff validation guard.
        Additional Comments: None.
        """
        with pytest.raises(ValueError, match="is_staff"):
            CustomUser.objects.create_superuser(
                email="bad@iitk.ac.in", name="Bad", password="pass1234", is_staff=False
            )

    @pytest.mark.django_db
    def test_create_superuser_not_superuser_raises(self):
        """
        Unit Name: Create superuser — is_superuser=False rejected
        Unit Details: Class CustomUserManager, function create_superuser
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Raises ValueError when is_superuser is explicitly False.
        Structural Coverage: Branch coverage — is_superuser validation guard.
        Additional Comments: None.
        """
        with pytest.raises(ValueError, match="is_superuser"):
            CustomUser.objects.create_superuser(
                email="bad2@iitk.ac.in", name="Bad2", password="pass1234", is_superuser=False
            )


# ═══════════════════════════════════════════════
#  CustomUser
# ═══════════════════════════════════════════════

class TestCustomUser:
    """Tests for the CustomUser model."""

    @pytest.mark.django_db
    def test_str(self, student_user):
        """
        Unit Name: CustomUser __str__
        Unit Details: Class CustomUser, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns 'Name (role)' format.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert str(student_user) == "Test Student (student)"

    @pytest.mark.django_db
    def test_default_role(self):
        """
        Unit Name: CustomUser default role
        Unit Details: Class CustomUser, field role
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Default role is 'student'.
        Structural Coverage: Statement coverage — field default verified.
        Additional Comments: None.
        """
        user = CustomUser.objects.create_user(
            email="def@iitk.ac.in", name="Default", password="pass1234"
        )
        assert user.role == "student"

    @pytest.mark.django_db
    def test_email_unique(self, student_user):
        """
        Unit Name: CustomUser unique email constraint
        Unit Details: Class CustomUser, field email (unique=True)
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: IntegrityError raised on duplicate email.
        Structural Coverage: Constraint coverage — unique email.
        Additional Comments: None.
        """
        with pytest.raises(IntegrityError):
            CustomUser.objects.create_user(
                email="student@iitk.ac.in", name="Dup", password="pass1234"
            )


# ═══════════════════════════════════════════════
#  Hall
# ═══════════════════════════════════════════════

class TestHall:
    """Tests for the Hall model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, hall):
        """
        Unit Name: Hall creation and __str__
        Unit Details: Class Hall, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Hall created successfully; __str__ returns the hall name.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert hall.pk is not None
        assert str(hall) == "Hall 1"

    @pytest.mark.django_db
    def test_unique_name(self, hall):
        """
        Unit Name: Hall unique name constraint
        Unit Details: Class Hall, field name (unique=True)
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: IntegrityError raised for duplicate name.
        Structural Coverage: Constraint coverage — unique name.
        Additional Comments: None.
        """
        with pytest.raises(IntegrityError):
            Hall.objects.create(name="Hall 1")


# ═══════════════════════════════════════════════
#  Item
# ═══════════════════════════════════════════════

class TestItem:
    """Tests for the Item model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, item, hall):
        """
        Unit Name: Item creation and __str__
        Unit Details: Class Item, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Item created with correct FK; __str__ returns 'name - hall_name'.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert item.pk is not None
        assert item.hall == hall
        assert str(item) == "Extra Roti - Hall 1"

    @pytest.mark.django_db
    def test_default_month(self, hall):
        """
        Unit Name: Item default month field
        Unit Details: Class Item, field month (default=current_month_name)
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: When month is not specified, defaults to current month name.
        Structural Coverage: Statement coverage — default callable invoked.
        Additional Comments: None.
        """
        i = Item.objects.create(name="Paneer", hall=hall, cost=Decimal("50.00"))
        assert i.month == current_month_name()


# ═══════════════════════════════════════════════
#  RebateApp
# ═══════════════════════════════════════════════

class TestRebateApp:
    """Tests for the RebateApp model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, rebate_app):
        """
        Unit Name: RebateApp creation and __str__
        Unit Details: Class RebateApp, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Created with default status 'pending'; __str__ returns expected format.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert rebate_app.status == "pending"
        assert str(rebate_app) == f"Rebate #{rebate_app.pk} - student@iitk.ac.in"

    @pytest.mark.django_db
    def test_status_choices(self, rebate_app):
        """
        Unit Name: RebateApp status mutation
        Unit Details: Class RebateApp, field status
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Status can be updated to 'approved' or 'rejected' and saved.
        Structural Coverage: Statement coverage for save path.
        Additional Comments: None.
        """
        rebate_app.status = "approved"
        rebate_app.save()
        rebate_app.refresh_from_db()
        assert rebate_app.status == "approved"


# ═══════════════════════════════════════════════
#  DailyRebateRefund
# ═══════════════════════════════════════════════

class TestDailyRebateRefund:
    """Tests for the DailyRebateRefund model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, daily_rebate_refund):
        """
        Unit Name: DailyRebateRefund creation and __str__
        Unit Details: Class DailyRebateRefund, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Created with month='April', cost=80; __str__ correct.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert daily_rebate_refund.cost == Decimal("80.00")
        assert str(daily_rebate_refund) == "Daily Rebate Refund - April"


# ═══════════════════════════════════════════════
#  Feedback
# ═══════════════════════════════════════════════

class TestFeedback:
    """Tests for the Feedback model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, feedback):
        """
        Unit Name: Feedback creation and __str__
        Unit Details: Class Feedback, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Created with default status 'pending'; __str__ correct.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert feedback.status == "pending"
        assert str(feedback) == f"Feedback #{feedback.pk} - Food Quality"


# ═══════════════════════════════════════════════
#  Cart
# ═══════════════════════════════════════════════

class TestCart:
    """Tests for the Cart model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, cart_item):
        """
        Unit Name: Cart creation and __str__
        Unit Details: Class Cart, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Cart entry created; __str__ returns expected format.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert cart_item.quantity == 2
        assert str(cart_item) == "Cart - student@iitk.ac.in / Extra Roti (x2)"

    @pytest.mark.django_db
    def test_unique_together(self, student_user, item):
        """
        Unit Name: Cart unique_together constraint
        Unit Details: Class Cart, Meta unique_together ('user', 'item')
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: IntegrityError on duplicate (user, item) pair.
        Structural Coverage: Constraint coverage.
        Additional Comments: None.
        """
        Cart.objects.create(user=student_user, item=item, quantity=1)
        with pytest.raises(IntegrityError):
            Cart.objects.create(user=student_user, item=item, quantity=3)


# ═══════════════════════════════════════════════
#  Booking
# ═══════════════════════════════════════════════

class TestBooking:
    """Tests for the Booking model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, booking):
        """
        Unit Name: Booking creation and __str__
        Unit Details: Class Booking, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Booking created with available_count=50; __str__ correct.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert booking.available_count == 50
        assert "Extra Roti" in str(booking)
        assert "50" in str(booking)

    @pytest.mark.django_db
    def test_unique_together(self, item, hall):
        """
        Unit Name: Booking unique_together constraint
        Unit Details: Class Booking, Meta unique_together ('item', 'hall', 'day_and_time')
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: IntegrityError on duplicate (item, hall, day_and_time) tuple.
        Structural Coverage: Constraint coverage.
        Additional Comments: None.
        """
        ts = timezone.now()
        Booking.objects.create(item=item, hall=hall, day_and_time=ts, available_count=10)
        with pytest.raises(IntegrityError):
            Booking.objects.create(item=item, hall=hall, day_and_time=ts, available_count=5)


# ═══════════════════════════════════════════════
#  MyBooking
# ═══════════════════════════════════════════════

class TestMyBooking:
    """Tests for the MyBooking model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, my_booking):
        """
        Unit Name: MyBooking creation and __str__
        Unit Details: Class MyBooking, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Created with status 'confirmed-not-scanned'; __str__ correct.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert my_booking.status == "confirmed-not-scanned"
        assert "CONFIRMED-NOT-SCANNED" in str(my_booking)

    @pytest.mark.django_db
    def test_status_update(self, my_booking):
        """
        Unit Name: MyBooking status update
        Unit Details: Class MyBooking, field status
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Status can be changed to 'confirmed-scanned' and saved.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        my_booking.status = "confirmed-scanned"
        my_booking.save()
        my_booking.refresh_from_db()
        assert my_booking.status == "confirmed-scanned"


# ═══════════════════════════════════════════════
#  QRDatabase
# ═══════════════════════════════════════════════

class TestQRDatabase:
    """Tests for the QRDatabase model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, qr_code):
        """
        Unit Name: QRDatabase creation and __str__
        Unit Details: Class QRDatabase, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: QR entry created; __str__ returns 'QR code - email'.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert str(qr_code) == "QR QR-TEST123456 - student@iitk.ac.in"

    @pytest.mark.django_db
    def test_unique_code(self, student_user):
        """
        Unit Name: QRDatabase unique code constraint
        Unit Details: Class QRDatabase, field code (unique=True)
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: IntegrityError raised for duplicate code.
        Structural Coverage: Constraint coverage.
        Additional Comments: None.
        """
        QRDatabase.objects.create(user=student_user, code="UNIQUE-001")
        with pytest.raises(IntegrityError):
            QRDatabase.objects.create(user=student_user, code="UNIQUE-001")


# ═══════════════════════════════════════════════
#  Menu
# ═══════════════════════════════════════════════

class TestMenu:
    """Tests for the Menu model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, menu):
        """
        Unit Name: Menu creation and __str__
        Unit Details: Class Menu, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Menu created; __str__ returns 'hall - day meal_time: dish'.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert str(menu) == "Hall 1 - Monday Lunch: Dal Rice"

    @pytest.mark.django_db
    def test_fields(self, menu):
        """
        Unit Name: Menu field values
        Unit Details: Class Menu, fields day/meal_time/dish/category
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: All fields match expected values.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert menu.day == "Monday"
        assert menu.meal_time == "Lunch"
        assert menu.dish == "Dal Rice"
        assert menu.category == "Veg"


# ═══════════════════════════════════════════════
#  Notification
# ═══════════════════════════════════════════════

class TestNotification:
    """Tests for the Notification model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, notification):
        """
        Unit Name: Notification creation and __str__
        Unit Details: Class Notification, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Created with default category 'unseen'; __str__ correct.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert notification.category == "unseen"
        assert str(notification) == "Test Notification - Test Student"

    @pytest.mark.django_db
    def test_mark_seen(self, notification):
        """
        Unit Name: Notification mark as seen
        Unit Details: Class Notification, field category
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Category can be updated from 'unseen' to 'seen'.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        notification.category = "seen"
        notification.save()
        notification.refresh_from_db()
        assert notification.category == "seen"


# ═══════════════════════════════════════════════
#  FixedCharges
# ═══════════════════════════════════════════════

class TestFixedCharges:
    """Tests for the FixedCharges model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, fixed_charges):
        """
        Unit Name: FixedCharges creation and __str__
        Unit Details: Class FixedCharges, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Created; __str__ returns expected format.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert fixed_charges.bill == Decimal("3000.00")
        assert str(fixed_charges) == "FixedCharges - student@iitk.ac.in / Hall 1"


# ═══════════════════════════════════════════════
#  BillVerification
# ═══════════════════════════════════════════════

class TestBillVerification:
    """Tests for the BillVerification model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, student_user):
        """
        Unit Name: BillVerification creation and __str__
        Unit Details: Class BillVerification, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Created; __str__ returns expected format with UUID.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        vid = uuid.uuid4()
        bv = BillVerification.objects.create(
            user=student_user, month="April", verification_id=vid, is_generated=True
        )
        assert str(bv) == f"BillVerification - student@iitk.ac.in / April / {vid}"


# ═══════════════════════════════════════════════
#  BillPaymentStatus
# ═══════════════════════════════════════════════

class TestBillPaymentStatus:
    """Tests for the BillPaymentStatus model."""

    @pytest.mark.django_db
    def test_creation_and_str(self, bill_payment_status):
        """
        Unit Name: BillPaymentStatus creation and __str__
        Unit Details: Class BillPaymentStatus, function __str__
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Created with default status 'unpaid'; __str__ correct.
        Structural Coverage: Statement coverage.
        Additional Comments: None.
        """
        assert bill_payment_status.status == "unpaid"
        assert str(bill_payment_status) == "BillPaymentStatus - student@iitk.ac.in / April / unpaid"

    @pytest.mark.django_db
    def test_unique_together(self, student_user):
        """
        Unit Name: BillPaymentStatus unique_together constraint
        Unit Details: Class BillPaymentStatus, Meta unique_together ('user', 'month')
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: IntegrityError on duplicate (user, month) pair.
        Structural Coverage: Constraint coverage.
        Additional Comments: None.
        """
        BillPaymentStatus.objects.create(user=student_user, month="March")
        with pytest.raises(IntegrityError):
            BillPaymentStatus.objects.create(user=student_user, month="March")
