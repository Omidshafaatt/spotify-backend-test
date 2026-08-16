python -m venv venv
venv\Scripts\Activate

pip install Django djangorestframework psycopg2-binary python-dotenv drf-spectacular

pip freeze > requirements.txt

django-admin startproject config . 


python manage.py migrate

python manage.py createsuperuser

python manage.py runserver

pip install Pillow

python manage.py shell

from subscriptions.models import SubscriptionPlan, SubscriptionPrice

# Create plans
base = SubscriptionPlan.objects.create(
    name="Base",
    max_daily_streams=60,
    max_playlists=5,
    can_upload_profile_image=False,
    can_download=False,
    can_early_access=False,
    can_view_statistics=False,
    is_active=True,
)

silver = SubscriptionPlan.objects.create(
    name="Silver",
    max_daily_streams=None,   # NULL
    max_playlists=100,
    can_upload_profile_image=True,
    can_download=True,
    can_early_access=False,
    can_view_statistics=False,
    is_active=True,
)

gold = SubscriptionPlan.objects.create(
    name="Gold",
    max_daily_streams=None,
    max_playlists=None,
    can_upload_profile_image=True,
    can_download=True,
    can_early_access=True,
    can_view_statistics=True,
    is_active=True,
)

# Add prices for Silver
silver_prices = [
    (1, 100000.00),
    (3, 250000.00),
    (6, 450000.00),
    (12, 800000.00),
]
for months, price in silver_prices:
    SubscriptionPrice.objects.create(
        plan=silver,
        duration_months=months,
        price=price,
        is_active=True,
    )

# Add prices for Gold
gold_prices = [
    (1, 200000.00),
    (3, 500000.00),
    (6, 900000.00),
    (12, 1400000.00),
]
for months, price in gold_prices:
    SubscriptionPrice.objects.create(
        plan=gold,
        duration_months=months,
        price=price,
        is_active=True,
    )

print("Plans and prices created successfully!")


pip install djangorestframework-simplejwt
pip install django-cors-headers
pip install requests
pip install python-dateutil