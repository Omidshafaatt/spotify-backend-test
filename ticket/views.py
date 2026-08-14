# music-streaming-backend/ticket/views.py
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404

from .models import Ticket, TicketMessage
from .serializers import (
    TicketSerializer,
    TicketMessageSerializer,
    TicketMessageCreateSerializer,
    TicketCreateSerializer
)
from accounts.permissions import IsAdminOrSupport, IsTicketOwnerOrAdminSupport
from accounts.models import User

# ----- Admin/Support Views (full access) -----

class TicketListView(generics.ListAPIView):
    """
    GET /tickets/
    Returns all tickets (admin/support only).
    Ordered: open and in_progress first, then created_at descending.
    """
    permission_classes = [IsAdminOrSupport]
    serializer_class = TicketSerializer

    def get_queryset(self):
        status_order = Case(
            When(status=Ticket.Status.OPEN, then=Value(1)),
            When(status=Ticket.Status.IN_PROGRESS, then=Value(2)),
            default=Value(3),
            output_field=IntegerField()
        )
        return Ticket.objects.annotate(
            status_order=status_order
        ).order_by('status_order', '-created_at')


class TicketMessageListView(generics.ListAPIView):
    """
    GET /tickets/<ticket_id>/messages/
    Returns all messages for a specific ticket (admin/support only).
    """
    permission_classes = [IsAdminOrSupport]
    serializer_class = TicketMessageSerializer

    def get_queryset(self):
        ticket_id = self.kwargs.get('ticket_id')
        get_object_or_404(Ticket, id=ticket_id)
        return TicketMessage.objects.filter(ticket_id=ticket_id).order_by('created_at')


# ----- User-facing endpoints (listener/artist) -----

class UserTicketListView(generics.ListAPIView):
    """
    GET /users/tickets/
    Returns tickets belonging to the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TicketSerializer

    def get_queryset(self):
        return Ticket.objects.filter(user=self.request.user).order_by('-created_at')


class UserTicketMessageListView(generics.ListAPIView):
    """
    GET /users/tickets/<ticket_id>/messages/
    Returns all messages for a ticket, but only if the ticket belongs to the current user,
    or if the user is admin/support (admin/support can see any ticket's messages).
    """
    permission_classes = [IsAuthenticated]   # we'll do ownership check inside
    serializer_class = TicketMessageSerializer

    def get_queryset(self):
        ticket_id = self.kwargs.get('ticket_id')
        ticket = get_object_or_404(Ticket, id=ticket_id)

        # Allow if admin/support OR the ticket owner
        user = self.request.user
        if user.role in (User.Role.ADMIN, User.Role.SUPPORT):
            # They can see all messages
            return TicketMessage.objects.filter(ticket_id=ticket_id).order_by('created_at')
        elif ticket.user == user:
            # Owner can see their own ticket's messages
            return TicketMessage.objects.filter(ticket_id=ticket_id).order_by('created_at')
        else:
            raise PermissionDenied("You do not have permission to view messages for this ticket.")


# ----- Create a Ticket Message (with status update & closed check) -----

class TicketMessageCreateView(generics.CreateAPIView):
    """
    POST /tickets/<ticket_id>/messages/
    Creates a new message on the ticket.

    - Only the ticket owner or admin/support may send messages.
    - Cannot send messages if the ticket is CLOSED.
    - If the sender is admin or support, the ticket status is updated to IN_PROGRESS.
    """
    permission_classes = [IsTicketOwnerOrAdminSupport]
    serializer_class = TicketMessageCreateSerializer

    def get_ticket(self):
        ticket_id = self.kwargs.get('ticket_id')
        ticket = get_object_or_404(Ticket, id=ticket_id)
        return ticket

    def perform_create(self, serializer):
        ticket = self.get_ticket()
        user = self.request.user

        # ---- Check closed ticket ----
        if ticket.status == Ticket.Status.CLOSED:
            raise PermissionDenied("Cannot add messages to a closed ticket.")

        # ---- Check permission on the ticket object ----
        if not IsTicketOwnerOrAdminSupport().has_object_permission(self.request, self, ticket):
            raise PermissionDenied("You do not have permission to send messages to this ticket.")

        # ---- Update ticket status if sender is admin/support ----
        if user.role in (User.Role.ADMIN, User.Role.SUPPORT):
            # Only change status if not already IN_PROGRESS or RESOLVED?
            if ticket.status != Ticket.Status.IN_PROGRESS:
                ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save(update_fields=['status'])

        # ---- Save the message ----
        serializer.save(ticket=ticket, sender=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = TicketMessage.objects.get(id=serializer.instance.id)
        response_serializer = TicketMessageSerializer(instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class TicketCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TicketCreateSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)