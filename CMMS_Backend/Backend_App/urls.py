from django.urls import path
from .views import (
    SignupView,
    LoginView,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordTemplateView,
    HallListView,
    UserProfileView,
    NotificationListView,
    MarkNotificationsSeenView,
    MenuListView,
    AuthStatusView,
    FeedbackListView,
    RebateAppListView,
    MessBillView,
    MyBookingListView
)

urlpatterns = [
    path('my/', AuthStatusView.as_view(), name='my'),
    path('menu/', MenuListView.as_view(), name='menu'),
    path('halls/', HallListView.as_view(), name='halls'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/mark-seen/', MarkNotificationsSeenView.as_view(), name='mark-notifications-seen'),
    path('feedbacks/', FeedbackListView.as_view(), name='feedbacks'),
    path('rebates/', RebateAppListView.as_view(), name='rebates'),
    path('mess-bill/', MessBillView.as_view(), name='mess-bill'),
    path('my-bookings/', MyBookingListView.as_view(), name='my-bookings'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/<uidb64>/<token>/', ResetPasswordTemplateView.as_view(), name='reset-password'),
]
