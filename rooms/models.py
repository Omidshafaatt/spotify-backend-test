# rooms/models.py
import uuid
from django.db import models
from django.conf import settings

class Room(models.Model):
    """
    مدل اتاق/گروه موقت برای اشتراک‌گذاری آهنگ
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="شناسه یکتای اتاق که در لینک دعوت استفاده می‌شود"
    )

    # اعضای اتاق (ارتباط ManyToMany با User)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="rooms",
        blank=True,
        help_text="کاربرانی که به این اتاق پیوسته‌اند"
    )

    # آهنگ فعلی (فایل صوتی)
    current_song = models.FileField(
        upload_to="room_songs/%Y/%m/%d/",
        null=True,
        blank=True,
        help_text="فایل صوتی که آخرین بار در اتاق آپلود شده است"
    )

    # عنوان آهنگ (اختیاری – از نام فایل می‌توان استخراج کرد)
    current_song_title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="عنوان آهنگ فعلی"
    )

    # موقعیت پخش (به ثانیه)
    current_position = models.FloatField(
        default=0.0,
        help_text="موقعیت پخش آهنگ به ثانیه"
    )

    # وضعیت پخش
    is_playing = models.BooleanField(
        default=False,
        help_text="آیا آهنگ در حال پخش است؟"
    )

    # زمان‌های ثبت
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "اتاق"
        verbose_name_plural = "اتاق‌ها"

    def __str__(self):
        return f"Room {self.id} - {self.members.count()} members"

    @property
    def member_count(self):
        """تعداد اعضای اتاق"""
        return self.members.count()

    def is_empty(self):
        """بررسی خالی بودن اتاق (بدون عضو)"""
        return self.member_count == 0

    def delete_if_empty(self):
        """حذف اتاق در صورت خالی بودن"""
        if self.is_empty():
            self.delete()
            return True
        return False