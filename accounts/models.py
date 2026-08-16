# music-streaming-backend/accounts/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, username, display_name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, display_name=display_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, display_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', self.model.Role.ADMIN)
        return self.create_user(email, username, display_name, password, **extra_fields)

class User(AbstractUser):
    class Role(models.TextChoices):
        LISTENER = "listener", "Listener"
        ARTIST = "artist", "Artist"
        SUPPORT = "support", "Support"
        ADMIN = "admin", "Admin"

    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=100)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    profile_image = models.ImageField(upload_to="profile_images/", null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.LISTENER)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "display_name"]

    def __str__(self):
        return self.email

# 🌟 کلاس Notification رو آوردیم بالا تا بقیه مدل‌ها بشناسنش
class Notification(models.Model):
    class Type(models.TextChoices):
        INFO = 'INFO', 'Info'
        WARNING = 'WARNING', 'Warning'
        SUCCESS = 'SUCCESS', 'Success'
        ERROR = 'ERROR', 'Error'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.INFO)
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.title}"

class Artist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="artist_profile")
    stage_name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.stage_name

class ArtistRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="artist_requests")
    stage_name = models.CharField(max_length=100)
    portfolio = models.URLField(max_length=500)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.stage_name} - {self.status}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None

        if not is_new:
            old_status = ArtistRequest.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        if is_new:
            staff_users = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPPORT])
            for staff in staff_users:
                Notification.objects.create(
                    user=staff,
                    title="New Artist Verification Request",
                    message=f"User {self.user.email} requested to become an artist (Stage name: {self.stage_name}).",
                    type=Notification.Type.WARNING,
                    link="/dashboard"
                )
        elif old_status != self.status:
            if self.status == self.Status.APPROVED:
                Notification.objects.create(
                    user=self.user,
                    title="Artist Request Approved!",
                    message="Congratulations! Your artist profile has been approved.",
                    type=Notification.Type.SUCCESS,
                    link="/studio"
                )
            elif self.status == self.Status.REJECTED:
                reason_text = f" Reason: {self.reason}" if self.reason else ""
                Notification.objects.create(
                    user=self.user,
                    title="Artist Request Rejected",
                    message=f"Unfortunately, your request was rejected.{reason_text}",
                    type=Notification.Type.ERROR,
                    link="/profile"
                )

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow"),
            models.CheckConstraint(condition=~models.Q(follower=models.F("following")), name="user_cannot_follow_themselves"),
        ]

    def __str__(self):
        return f"{self.follower} follows {self.following}"

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    language = models.CharField(max_length=10, default='en')
    notifications = models.CharField(max_length=20, default='mentions')
    volume = models.FloatField(default=1.0)

    def __str__(self):
        return f"Settings for {self.user.email}"