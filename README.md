# Central Mess Management System (CMMS) - Backend

This is the backend for the Central Mess Management System (CMMS), a comprehensive platform for managing mess operations, including student registration, menu management, rebate applications, feedback tracking, and automated billing.

## Features

- **Robust Authentication**: JWT-based authentication with Refresh Token rotation and secure cookie storage. Supports Student and Admin roles.
- **Mess Menu Management**: Dynamic weekly menus for multiple halls, categorized by meal type (Breakfast, Lunch, Snacks, Dinner).
- **Automated Billing System**: Calculates monthly bills based on:
    - Fixed mess charges.
    - Extras/add-ons purchased via the booking system.
    - Approved rebate deductions.
- **Extras Booking (Cart System)**:
    - Real-time inventory tracking for extra items.
    - Integrated cart for multiple bookings.
    - QR Code generation for seamless item collection.
- **Rebate Management**: Streamlined application process for student leave periods with admin approval workflows.
- **Feedback & Complaints**: Centralized system for students to submit feedback and track resolution status.
- **Real-time Notifications**: Automated alerts for rebate status updates, billing, and system announcements.
- **Admin Dashboard**: Comprehensive tools for managing students, halls, menus, and financial reports.

## Tech Stack

- **Framework**: [Django 6.0](https://www.djangoproject.com/) & [Django REST Framework](https://www.django-rest-framework.org/)
- **Language**: Python 3.12+
- **Database**: PostgreSQL (Production), SQLite (Development)
- **Authentication**: [SimpleJWT](https://django-rest-framework-simplejwt.readthedocs.io/)
- **Package Management**: [Poetry](https://python-poetry.org/)
- **Email Service**: Brevo API
- **Static Files**: WhiteNoise

## Installation & Setup

### Prerequisites
- Python 3.12 or higher
- [Poetry](https://python-poetry.org/docs/#installation) installed on your system

### 1. Clone the repository
```bash
git clone <repository-url>
cd New-CMMS-Backend
```

### 2. Install dependencies
```bash
poetry install --no-root
```

### 3. Configure Environment Variables
Create a `.env` file in the `CMMS_Backend/` directory (where `manage.py` is located) and add the following:

```env
SECRET_KEY_SETTINGS="your-secure-secret-key"
DEBUG="True"
SECURE="False"
SAMESITE="Lax"
FRONTEND_URL="http://localhost:5173"
BREVO_API_KEY="your-brevo-api-key"
EMAIL_HOST_USER="your-sender-email"
```

### 4. Run Migrations
```bash
poetry run python CMMS_Backend/manage.py migrate
```

### 5. Create a Superuser (Admin)
```bash
poetry run python CMMS_Backend/manage.py createsuperuser
```

### 6. Start the Development Server
```bash
poetry run python CMMS_Backend/manage.py runserver localhost:8000
```
The API will be available at `http://localhost:8000/`.

## Project Structure

- `CMMS_Backend/`: Main Django project directory.
    - `mysite/`: Project settings and root URL configuration.
    - `Backend_App/`: Core application logic (Models, Views, Serializers).
    - `staticfiles/`: Collected static files for production.
- `pyproject.toml`: Poetry dependency definitions.

## Post-Deployment Note
In `settings.py`, ensure `SECURE_SSL_REDIRECT` and cookie security flags are properly configured for production environments (handled automatically when `DEBUG=False`).

---

