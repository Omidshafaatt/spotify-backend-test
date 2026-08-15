# music-streaming-backend/accounts/permissions.py
from rest_framework.permissions import BasePermission
from .models import User

class IsAdmin(BasePermission):
    """
    Allows access only to users with 'admin' role.
    """
    def has_permission(self, request, view):
        return (request.user.is_authenticated and
                request.user.role == User.Role.ADMIN)

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

class IsTicketOwnerOrAdminSupport(BasePermission):
    """
    Allows access if:
    - the user is the owner of the ticket (the user who created it), OR
    - the user has admin/support role.
    Used for retrieving a single ticket, updating, or posting messages.
    """
    def has_object_permission(self, request, view, obj):
        # obj is a Ticket instance
        if request.user.is_authenticated:
            if request.user.role in (User.Role.ADMIN, User.Role.SUPPORT):
                return True
            return obj.user == request.user
        return False

    def has_permission(self, request, view):
        # For creation (POST) we don't have an object yet,
        # so we check authentication and then verify the ticket in the view.
        return request.user.is_authenticated