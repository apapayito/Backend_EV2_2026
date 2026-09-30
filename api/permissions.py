from rest_framework.permissions import BasePermission


class IsCoordinator(BasePermission):
    """Autoriza únicamente coordinadores académicos o superusuarios."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.is_superuser or
            getattr(getattr(request.user, 'profile', None), 'role', None) == 'COORDINATOR'
        ))