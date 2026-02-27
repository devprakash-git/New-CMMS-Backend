from django.urls import path
from .views import (
    SignupView,
    LoginView,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordTemplateView
)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/<uidb64>/<token>/', ResetPasswordTemplateView.as_view(), name='reset-password'),
]
