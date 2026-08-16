# ticket/tests.py
from datetime import date

from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Ticket, TicketMessage


class TicketAPITests(APITestCase):

    def create_user(self, email, display_name, role):
        return User.objects.create_user(
            username=f"test_{display_name}",
            email=email,
            display_name=display_name,
            password="TestPassword123!",
            birth_date=date(2000, 1, 1),
            gender="male",
            role=role,
        )

    def create_ticket(self, user, subject="Test Ticket", status=None):
        data = {
            "user": user,
            "subject": subject,
        }

        if status is not None:
            data["status"] = status

        return Ticket.objects.create(**data)

    # --------------------------------------------------
    # 1. User can create a ticket
    # --------------------------------------------------

    def test_user_can_create_ticket(self):
        user = self.create_user(
            email="user@example.com",
            display_name="TestUser",
            role=User.Role.LISTENER,
        )

        self.client.force_authenticate(user=user)

        url = reverse("create-ticket")

        response = self.client.post(
            url,
            {
                "subject": "I have a problem with my subscription",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        ticket = Ticket.objects.get(
            subject="I have a problem with my subscription"
        )

        self.assertEqual(ticket.user, user)

    # --------------------------------------------------
    # 2. User can only see their own tickets
    # --------------------------------------------------

    def test_user_can_only_see_own_tickets(self):
        user1 = self.create_user(
            email="user1@example.com",
            display_name="UserOne",
            role=User.Role.LISTENER,
        )

        user2 = self.create_user(
            email="user2@example.com",
            display_name="UserTwo",
            role=User.Role.LISTENER,
        )

        self.create_ticket(
            user=user1,
            subject="User 1 Ticket",
        )

        self.create_ticket(
            user=user2,
            subject="User 2 Ticket",
        )

        self.client.force_authenticate(user=user1)

        url = reverse("user-ticket-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["subject"],
            "User 1 Ticket",
        )

    # --------------------------------------------------
    # 3. Ticket owner can send a message
    # --------------------------------------------------

    def test_ticket_owner_can_send_message(self):
        user = self.create_user(
            email="owner@example.com",
            display_name="TicketOwner",
            role=User.Role.LISTENER,
        )

        ticket = self.create_ticket(
            user=user,
            subject="Problem with music playback",
        )

        self.client.force_authenticate(user=user)

        url = reverse(
            "ticket-message-create",
            kwargs={"ticket_id": ticket.id},
        )

        response = self.client.post(
            url,
            {
                "message": "The music stops playing after a few seconds.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        message = TicketMessage.objects.get(
            ticket=ticket
        )

        self.assertEqual(message.sender, user)
        self.assertEqual(
            message.message,
            "The music stops playing after a few seconds.",
        )

    # --------------------------------------------------
    # 4. Admin/support message changes ticket status
    # --------------------------------------------------

    def test_admin_message_changes_ticket_status_to_in_progress(self):
        user = self.create_user(
            email="ticketowner@example.com",
            display_name="TicketOwner",
            role=User.Role.LISTENER,
        )

        support = self.create_user(
            email="support@example.com",
            display_name="SupportUser",
            role=User.Role.SUPPORT,
        )

        ticket = self.create_ticket(
            user=user,
            subject="Support needed",
        )

        self.client.force_authenticate(user=support)

        url = reverse(
            "ticket-message-create",
            kwargs={"ticket_id": ticket.id},
        )

        response = self.client.post(
            url,
            {
                "message": "We are looking into your problem.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        ticket.refresh_from_db()

        self.assertEqual(
            ticket.status,
            Ticket.Status.IN_PROGRESS,
        )

        message = TicketMessage.objects.get(
            ticket=ticket
        )

        self.assertEqual(message.sender, support)

    # --------------------------------------------------
    # 5. Cannot send message to a closed ticket
    # --------------------------------------------------

    def test_cannot_send_message_to_closed_ticket(self):
        user = self.create_user(
            email="closed@example.com",
            display_name="ClosedTicketUser",
            role=User.Role.LISTENER,
        )

        ticket = self.create_ticket(
            user=user,
            subject="Already resolved problem",
            status=Ticket.Status.CLOSED,
        )

        self.client.force_authenticate(user=user)

        url = reverse(
            "ticket-message-create",
            kwargs={"ticket_id": ticket.id},
        )

        response = self.client.post(
            url,
            {
                "message": "I want to send another message.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            TicketMessage.objects.filter(
                ticket=ticket
            ).exists()
        )