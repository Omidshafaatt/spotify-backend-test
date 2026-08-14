# music-streaming-backend/ticket/urls.py
from django.urls import path
from .views import (
    TicketListView,
    TicketMessageListView,
    TicketMessageCreateView,
    UserTicketListView,
    UserTicketMessageListView,
    TicketCreateView,
)

urlpatterns = [
    # Admin/Support endpoints
    path('tickets/', TicketListView.as_view(), name='ticket-list'),
    path('tickets/create/', TicketCreateView.as_view(), name='create-ticket'),
    path('tickets/<int:ticket_id>/messages/', TicketMessageListView.as_view(), name='ticket-messages-list'),
    path('tickets/<int:ticket_id>/messages/create/', TicketMessageCreateView.as_view(), name='ticket-message-create'),

    # User endpoints (listener/artist)
    path('users/tickets/', UserTicketListView.as_view(), name='user-ticket-list'),
    path('users/tickets/<int:ticket_id>/messages/', UserTicketMessageListView.as_view(), name='user-ticket-messages'),
]