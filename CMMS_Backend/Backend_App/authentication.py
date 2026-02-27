from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom authentication class that reads JWT from HttpOnly cookies
    instead of the Authorization header.
    """

    def authenticate(self, request):
        raw_token = request.COOKIES.get("access_token")

        if raw_token is None:
            return None  # DRF will treat as anonymous

        try:
            validated_token = self.get_validated_token(raw_token)
        except Exception:
            raise AuthenticationFailed("Invalid or expired token")

        return self.get_user(validated_token), validated_token
