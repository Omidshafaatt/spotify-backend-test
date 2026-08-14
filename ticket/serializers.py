# music-streaming-backend/ticket/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Ticket, TicketMessage

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'display_name']


class TicketSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'user', 'subject', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class TicketMessageSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(read_only=True)

    class Meta:
        model = TicketMessage
        fields = [
            'id', 'ticket', 'sender', 'message', 'created_at'
        ]
        read_only_fields = fields


class TicketMessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer used only for creating a new message.
    The client only needs to send the message text.
    """
    class Meta:
        model = TicketMessage
        fields = ['message']

class TicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['subject']