from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Permits access only to users whose CustomUser.role is 'admin'.

    Returns 403 Forbidden with a descriptive error for non-admin users.
    This is enforced at the DRF permission layer — before any view logic
    executes — so there is no way to bypass it by forgetting an inline check.
    """

    message = "Admin access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", "") == "admin"
        )
