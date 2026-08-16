# music-streaming-backend/ticket/models.py
from django.conf import settings
from django.db import models


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets",
    )

    subject = models.CharField(
        max_length=200,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"#{self.id} - {self.subject}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            # وارد کردن مدل‌ها برای جلوگیری از Circular Import
            from accounts.models import Notification, User
            
            # پیدا کردن مدیران و پشتیبان‌ها
            staff_users = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPPORT])
            
            for staff in staff_users:
                Notification.objects.create(
                    user=staff,
                    title="New Support Ticket",
                    message=f"User {self.user.email} submitted a new ticket: #{self.id} - {self.subject}",
                    type=Notification.Type.WARNING,
                    link="/dashboard" # یا هر لینکی که داشبورد پشتیبان‌هاست
                )

class TicketMessage(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_messages",
    )

    message = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"Ticket #{self.ticket.id} - {self.sender.email}"

