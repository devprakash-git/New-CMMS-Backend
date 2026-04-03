"""
Unit tests for CookieJWTAuthentication in Backend_App.authentication.
Verifies cookie-based JWT authentication: missing cookie, valid token,
and invalid/expired token scenarios.
"""

import pytest
from django.test import RequestFactory
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from Backend_App.authentication import CookieJWTAuthentication
from Backend_App.models import CustomUser


class TestCookieJWTAuthentication:
    """Tests for the CookieJWTAuthentication class."""

    @pytest.mark.django_db
    def test_no_cookie_returns_none(self):
        """
        Unit Name: CookieJWTAuthentication — no cookie
        Unit Details: Class CookieJWTAuthentication, function authenticate
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns None when access_token cookie is absent (anonymous request).
        Structural Coverage: Branch coverage — raw_token is None path.
        Additional Comments: DRF treats None as anonymous; no error raised.
        """
        factory = RequestFactory()
        request = factory.get("/api/my/")
        auth = CookieJWTAuthentication()
        result = auth.authenticate(request)
        assert result is None

    @pytest.mark.django_db
    def test_valid_token_authenticates(self, student_user):
        """
        Unit Name: CookieJWTAuthentication — valid token
        Unit Details: Class CookieJWTAuthentication, function authenticate
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Returns (user, validated_token) tuple when cookie has valid JWT.
        Structural Coverage: Statement coverage — happy path through get_validated_token and get_user.
        Additional Comments: Uses RefreshToken.for_user to generate a real access token.
        """
        refresh = RefreshToken.for_user(student_user)
        access_token = str(refresh.access_token)

        factory = RequestFactory()
        request = factory.get("/api/my/")
        request.COOKIES["access_token"] = access_token

        auth = CookieJWTAuthentication()
        user, token = auth.authenticate(request)
        assert user.id == student_user.id

    @pytest.mark.django_db
    def test_invalid_token_raises(self):
        """
        Unit Name: CookieJWTAuthentication — invalid/expired token
        Unit Details: Class CookieJWTAuthentication, function authenticate
        Test Date: 04/03/2026 - 04/03/2026
        Test Results: Raises AuthenticationFailed when cookie contains invalid JWT.
        Structural Coverage: Branch coverage — exception handler path.
        Additional Comments: None.
        """
        factory = RequestFactory()
        request = factory.get("/api/my/")
        request.COOKIES["access_token"] = "totally-invalid-jwt"

        auth = CookieJWTAuthentication()
        with pytest.raises(AuthenticationFailed, match="Invalid or expired"):
            auth.authenticate(request)
