"""
Shared pytest fixtures for Backend_App unit tests.
Provides reusable model instances and pre-authenticated API clients.
"""

import pytest
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient

from Backend_App.models import (
    CustomUser, Hall, Item, Booking, Menu, Notification,
    Feedback, RebateApp, DailyRebateRefund, Cart, MyBooking,
    QRDatabase, FixedCharges, BillVerification, BillPaymentStatus,
)


@pytest.fixture
def api_client():
    """Return a plain (unauthenticated) DRF APIClient."""
    return APIClient()


@pytest.fixture
def hall(db):
    """Create and return a Hall instance named 'Hall 1'."""
    return Hall.objects.create(name="Hall 1")


@pytest.fixture
def hall2(db):
    """Create and return a second Hall instance named 'Hall 2'."""
    return Hall.objects.create(name="Hall 2")


@pytest.fixture
def student_user(db, hall):
    """Create and return a student user assigned to Hall 1."""
    return CustomUser.objects.create_user(
        email="student@iitk.ac.in",
        name="Test Student",
        password="testpass1234",
        roll_no="220001",
        hall_of_residence=hall,
        room_no="101",
        contact_no="9876543210",
        role="student",
    )


@pytest.fixture
def student_user2(db, hall):
    """Create and return a second student user."""
    return CustomUser.objects.create_user(
        email="student2@iitk.ac.in",
        name="Test Student 2",
        password="testpass1234",
        roll_no="220002",
        hall_of_residence=hall,
        role="student",
    )


@pytest.fixture
def admin_user(db):
    """Create and return an admin user."""
    return CustomUser.objects.create_user(
        email="admin@iitk.ac.in",
        name="Test Admin",
        password="adminpass1234",
        role="admin",
        is_staff=True,
    )


@pytest.fixture
def authenticated_client(api_client, student_user):
    """Return an APIClient force-authenticated as the student user."""
    api_client.force_authenticate(user=student_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an APIClient force-authenticated as the admin user."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def item(db, hall):
    """Create and return an Item in Hall 1."""
    return Item.objects.create(name="Extra Roti", hall=hall, cost=Decimal("10.00"), month="April")


@pytest.fixture
def booking(db, item, hall):
    """Create and return a Booking slot for the test item."""
    return Booking.objects.create(
        item=item,
        hall=hall,
        day_and_time=timezone.now(),
        available_count=50,
    )


@pytest.fixture
def menu(db, hall):
    """Create and return a Menu entry for Hall 1."""
    return Menu.objects.create(
        hall=hall,
        day="Monday",
        meal_time="Lunch",
        dish="Dal Rice",
        category="Veg",
    )


@pytest.fixture
def notification(db, student_user):
    """Create and return an unseen notification for the student."""
    return Notification.objects.create(
        user=student_user,
        title="Test Notification",
        content="This is a test.",
        category="unseen",
    )


@pytest.fixture
def feedback(db, student_user):
    """Create and return a Feedback entry."""
    return Feedback.objects.create(
        user=student_user,
        category="Food Quality",
        content="The food was cold.",
    )


@pytest.fixture
def rebate_app(db, student_user):
    """Create and return a RebateApp entry."""
    from datetime import date
    return RebateApp.objects.create(
        user=student_user,
        start_date=date(2026, 4, 5),
        end_date=date(2026, 4, 10),
        location="Home",
    )


@pytest.fixture
def daily_rebate_refund(db):
    """Create and return a DailyRebateRefund for April."""
    return DailyRebateRefund.objects.create(month="April", cost=Decimal("80.00"))


@pytest.fixture
def cart_item(db, student_user, item):
    """Create and return a Cart entry."""
    return Cart.objects.create(user=student_user, item=item, quantity=2)


@pytest.fixture
def qr_code(db, student_user):
    """Create and return a QRDatabase entry."""
    return QRDatabase.objects.create(user=student_user, code="QR-TEST123456")


@pytest.fixture
def my_booking(db, student_user, booking, qr_code):
    """Create and return a MyBooking entry."""
    return MyBooking.objects.create(
        user=student_user,
        booking=booking,
        qr_code=qr_code,
        quantity=2,
        status="confirmed-not-scanned",
    )


@pytest.fixture
def fixed_charges(db, student_user, hall):
    """Create and return a FixedCharges entry."""
    return FixedCharges.objects.create(
        user=student_user,
        hall=hall,
        category="Mess Basic",
        bill=Decimal("3000.00"),
    )


@pytest.fixture
def bill_payment_status(db, student_user):
    """Create and return a BillPaymentStatus entry."""
    return BillPaymentStatus.objects.create(
        user=student_user, month="April", status="unpaid"
    )
