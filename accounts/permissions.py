# music-streaming-backend/accounts/permissions.py
from rest_framework.permissions import BasePermission
from .models import User


class IsAdminOrSupport(BasePermission):
    """
    Allows access only to users with 'admin' or 'support' role.
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                request.user.role in (User.Role.ADMIN, User.Role.SUPPORT))

class IsListenerOrArtist(BasePermission):
    """
    Allows access only to users with 'listener' or 'artist' role.
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                request.user.role in (User.Role.LISTENER, User.Role.ARTIST))