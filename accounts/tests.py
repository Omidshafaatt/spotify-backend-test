# accounts/tests.py
from datetime import date

from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import User, Follow


class AccountAPITests(APITestCase):

    def create_listener(self, email, display_name):
        return User.objects.create_user(
            username=f"test_{display_name}",
            email=email,
            display_name=display_name,
            password="TestPassword123!",
            birth_date=date(2000, 1, 1),
            gender="male",
            role=User.Role.LISTENER,
        )

    # --------------------------------------------------
    # 1. Successful registration
    # --------------------------------------------------

    def test_listener_registration_success(self):
        url = reverse("listener-register")

        data = {
            "email": "newuser@example.com",
            "display_name": "NewUser",
            "birth_date": "2000-01-01",
            "gender": "male",
            "password": "StrongPassword123!",
            "password2": "StrongPassword123!",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 201)

        user = User.objects.get(email="newuser@example.com")

        self.assertEqual(user.display_name, "NewUser")
        self.assertEqual(user.role, User.Role.LISTENER)
        self.assertTrue(user.check_password("StrongPassword123!"))

    # --------------------------------------------------
    # 2. Registration with duplicate email
    # --------------------------------------------------

    def test_listener_registration_duplicate_email(self):
        self.create_listener(
            email="existing@example.com",
            display_name="ExistingUser",
        )

        url = reverse("listener-register")

        data = {
            "email": "existing@example.com",
            "display_name": "AnotherUser",
            "birth_date": "2000-01-01",
            "gender": "male",
            "password": "StrongPassword123!",
            "password2": "StrongPassword123!",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            User.objects.filter(email="existing@example.com").count(),
            1,
        )

    # --------------------------------------------------
    # 3. Successful login
    # --------------------------------------------------

    def test_login_success(self):
        user = self.create_listener(
            email="login@example.com",
            display_name="LoginUser",
        )

        url = reverse("login")

        data = {
            "email": "login@example.com",
            "password": "TestPassword123!",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 200)

        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

        self.assertEqual(response.data["user"]["id"], user.id)
        self.assertEqual(
            response.data["user"]["email"],
            "login@example.com",
        )

    # --------------------------------------------------
    # 4. Successful follow
    # --------------------------------------------------

    def test_follow_user_success(self):
        follower = self.create_listener(
            email="follower@example.com",
            display_name="Follower",
        )

        following = self.create_listener(
            email="following@example.com",
            display_name="Following",
        )

        self.client.force_authenticate(user=follower)

        url = reverse("follow")

        data = {
            "display_name": following.display_name,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 201)

        self.assertTrue(
            Follow.objects.filter(
                follower=follower,
                following=following,
            ).exists()
        )

    # --------------------------------------------------
    # 5. User cannot follow themselves
    # --------------------------------------------------

    def test_user_cannot_follow_themselves(self):
        user = self.create_listener(
            email="self@example.com",
            display_name="SelfUser",
        )

        self.client.force_authenticate(user=user)

        url = reverse("follow")

        data = {
            "display_name": user.display_name,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, 400)

        self.assertFalse(
            Follow.objects.filter(
                follower=user,
                following=user,
            ).exists()
        )