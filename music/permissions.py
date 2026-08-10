# music-streaming-backend/music/permissions.py
from rest_framework.permissions import BasePermission
from accounts.models import User


class IsListenerOrArtist(BasePermission):
    """
    Allows access only to users with 'listener' or 'artist' role.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (User.Role.LISTENER, User.Role.ARTIST)