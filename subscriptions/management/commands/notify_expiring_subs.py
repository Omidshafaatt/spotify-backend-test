from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from subscriptions.models import UserSubscription
from accounts.models import Notification

class Command(BaseCommand):
    help = 'Check for expiring subscriptions (31 days) and notify users'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        
        # تنظیم دقیق روی ۳۱ روز آینده
        target_date = now + timedelta(days=31)

        # پیدا کردن اشتراک‌های فعال که تاریخ پایانشون کمتر از ۳۱ روز دیگه‌ست
        expiring_subs = UserSubscription.objects.filter(
            status=UserSubscription.Status.ACTIVE,
            end_date__isnull=False,
            end_date__lte=target_date, 
            end_date__gte=now          
        )

        count = 0
        for sub in expiring_subs:
            # ارسال نوتیفیکیشن هشدار اتمام
            Notification.objects.create(
                user=sub.user,
                title="Subscription Expiring Soon!",
                message=f"Your {sub.subscription_price.plan.name} subscription will expire on {sub.end_date.strftime('%B %d, %Y')}. Renew now to keep your premium benefits!",
                type=Notification.Type.WARNING,
                link="/subscriptions" # هدایت کاربر به صفحه خرید اشتراک
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully sent expiration notifications to {count} users.'))