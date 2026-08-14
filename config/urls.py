# music-streaming-backend/config/urls.py
"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
"""
URL configuration for config project.
"""
import mimetypes
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# این تنظیم برای رفع باگ شناخته‌نشدن فرمت m4a در ویندوز است
mimetypes.add_type("audio/mp4", ".m4a")

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # مسیر اپلیکیشن‌ها
    path('accounts/', include('accounts.urls')),
    path('music/', include('music.urls')),
    path('subscriptions/', include('subscriptions.urls')),
    path('ticket/', include('ticket.urls')),

    # OpenAPI schema and Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# به جنگو می‌گوییم فایل‌های مدیا را در حالت دیباگ سرو کند
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
