from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from datetime import timedelta
import calendar as _calendar
import datetime as _datetime


def current_month_name():
    """Returns the current month name, e.g. 'March'. Used as a model field default."""
    return _datetime.date.today().strftime("%B")

def get_cart_expiry():
    return timezone.now() + timedelta(days=7)
# ──────────────────────────────────────────────
# User Manager ────────────────────────────────
# ──────────────────────────────────────────────
class CustomUserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            name=name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, name, password, **extra_fields)

# ──────────────────────────────────────────────
# User

# ──────────────────────────────────────────────
class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    
    # Made these blank=True so Admin accounts don't require student-specific fields
    roll_no = models.CharField(max_length=50, blank=True, default='')
    hall_of_residence = models.ForeignKey('Hall', on_delete=models.SET_NULL, null=True, blank=True, related_name='residents')
    room_no = models.CharField(max_length=20, blank=True, default='')
    contact_no = models.CharField(max_length=15, blank=True, default='')
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name'] # Removed roll_no/hall to prevent superuser creation errors

    def __str__(self):
        return f"{self.name} ({self.role})"

# ──────────────────────────────────────────────
# Hall
# ──────────────────────────────────────────────
class Hall(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

# ──────────────────────────────────────────────
# Item  (linked to a Hall / category)
# ──────────────────────────────────────────────
class Item(models.Model):
    name = models.CharField(max_length=255)
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='items')
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    month = models.CharField(max_length=20, default=current_month_name)  # e.g. "March"

    def __str__(self):
        return f"{self.name} - {self.hall.name}"

# ──────────────────────────────────────────────
# Rebate Application
# ──────────────────────────────────────────────
class RebateApp(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='rebate_apps')
    # Replaced 'store_food' with actual leave dates as per handwritten diagram
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Rebate #{self.pk} - {self.user.email}"

class DailyRebateRefund(models.Model):
    month = models.CharField(max_length=20, default=current_month_name)  # e.g. "March"
    cost = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Daily Rebate Refund - {self.month}"

# ──────────────────────────────────────────────
# Feedback / Complaint
# ──────────────────────────────────────────────
class Feedback(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='feedbacks')
    category = models.CharField(max_length=255)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    content = models.TextField()

    def __str__(self):
        return f"Feedback #{self.pk} - {self.category}"

# ──────────────────────────────────────────────
# Cart
# ──────────────────────────────────────────────
class Cart(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cart_items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='cart_entries')
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('user', 'item')

    # For the Admin Panel
    def __str__(self):
        return f"Cart - {self.user.email} / {self.item.name} (x{self.quantity})"


# ──────────────────────────────────────────────
# Booking  (Inventory / Availability Slot)
# ──────────────────────────────────────────────
class Booking(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='bookings')
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='bookings')
    day_and_time = models.DateTimeField()

    
    # Added count/capacity based on the handwritten diagram to prevent infinite overbooking
    available_count = models.PositiveIntegerField(default=0)

    class Meta:
        # Prevents duplicate availability slots for the same item/time/hall
        unique_together = ('item', 'hall', 'day_and_time')
        constraints = [
            models.CheckConstraint(
                condition=models.Q(available_count__gte=0),
                name='booking_available_count_non_negative',
            ),
        ]
    
    def __str__(self):
        return f"Slot #{self.pk} - {self.item.name} (Avail: {self.available_count})"

# ──────────────────────────────────────────────
# My Booking  (user's confirmed booking → QR code)
# ──────────────────────────────────────────────
class MyBooking(models.Model):
    STATUS_CHOICES = [
        ('confirmed-not-scanned', 'Confirmed-Not-Scanned'),
        ('confirmed-scanned', 'Confirmed-Scanned'),
        ('cancelled', 'Cancelled')
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='my_bookings')
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='user_bookings')
    qr_code = models.ForeignKey('QRDatabase', on_delete=models.CASCADE, related_name='my_bookings', null=True)
    
    # Added quantity and status for order management
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='confirmed-not-scanned')
    booked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MyBooking #{self.pk} - {self.status.upper()}"

# ──────────────────────────────────────────────
# QR Database
# ──────────────────────────────────────────────
class QRDatabase(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='qr_codes')
    code = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"QR {self.code} - {self.user.email}"

# ──────────────────────────────────────────────
# Menu
# ──────────────────────────────────────────────
class Menu(models.Model):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]
    MEAL_CHOICES = [
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Snacks', 'Snacks'),
        ('Dinner', 'Dinner'),
    ]

    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='menus')
    day = models.CharField(max_length=20, choices=DAY_CHOICES, default='Monday')
    meal_time = models.CharField(max_length=20, choices=MEAL_CHOICES, default='Breakfast')
    dish = models.CharField(max_length=255)
    category = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.hall.name} - {self.day} {self.meal_time}: {self.dish}"



class Notification(models.Model):
    CATEGORY_CHOICES = [
        ('seen', 'Seen'),
        ('unseen', 'Unseen'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    content = models.TextField()

    category = models.CharField(
        max_length=10,
        choices=CATEGORY_CHOICES,
        default='unseen'
    )

    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.name}"

class FixedCharges(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='fixed_charges')
    bill = models.DecimalField(max_digits=10, decimal_places=2)
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='fixed_charges')
    category = models.CharField(max_length=100)

    def __str__(self):
        return f"FixedCharges - {self.user.email} / {self.hall.name}"

# ──────────────────────────────────────────────
# Bill Verification (for PDF generation)
# ──────────────────────────────────────────────
class BillVerification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bill_verifications')
    month = models.CharField(max_length=20)                              # e.g. "March"
    verification_id = models.UUIDField(unique=True)
    is_generated = models.BooleanField(default=False)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"BillVerification - {self.user.email} / {self.month} / {self.verification_id}"

# ──────────────────────────────────────────────
# Bill Payment Status (tracks paid/unpaid per student per month)
# ──────────────────────────────────────────────
class BillPaymentStatus(models.Model):
    BILL_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bill_statuses')
    month = models.CharField(max_length=20)                              # e.g. "March"
    status = models.CharField(max_length=10, choices=BILL_STATUS_CHOICES, default='unpaid')
    paid_on = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'month')

    def __str__(self):
        return f"BillPaymentStatus - {self.user.email} / {self.month} / {self.status}"