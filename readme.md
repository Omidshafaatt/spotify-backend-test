# Spotify Backend

A Django REST Framework backend for a Spotify-like music streaming application, using PostgreSQL as the database.

## Prerequisites

Make sure you have the following installed:

- Python 3.x
- PostgreSQL
- Git

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Omidshafaatt/spotify-backend-test.git
cd spotify-backend-test
```

### 2. Create the `.env` file

Create a `.env` file in the project root directory and add the following configuration:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True

DB_NAME=your-db-name
DB_USER=db-user
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

ZARINPAL_MERCHANT_ID=your-random-uuid
```

Replace the placeholder values with your actual PostgreSQL database credentials.

### 3. Create and activate a virtual environment

Create the virtual environment:

```bash
python -m venv venv
```

On **Windows**, activate it with:

```powershell
.\venv\Scripts\Activate
```

On **Linux/macOS**, use:

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Apply database migrations

Create migrations if necessary:

```bash
python manage.py makemigrations
```

Then apply them:

```bash
python manage.py migrate
```

### 6. Create a superuser

Create an admin account for accessing the Django admin panel:

```bash
python manage.py createsuperuser
```

Follow the prompts and enter the required information.

## 7. Create Subscription Plans

Open the Django shell:

```bash
python manage.py shell
```

Then run the following code:

```python
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
    max_daily_streams=None,
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
```

After running the code, exit the Django shell:

```python
exit()
```

## 8. Run the Development Server

Start the Django development server:

```bash
python manage.py runserver
```

By default, the backend will be available at:

```text
http://127.0.0.1:8000/
```

## Admin Panel

You can access the Django admin panel at:

```text
http://127.0.0.1:8000/admin/
```

Use the superuser credentials created during the setup process to log in.

## Project Structure

The project is built with:

- **Django** — Web framework
- **Django REST Framework** — REST API
- **PostgreSQL** — Database
- **ZarinPal** — Payment gateway
- **Python virtual environment** — Dependency isolation