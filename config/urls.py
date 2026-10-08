from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from lucky_receipt.views import RegisterView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/register/", RegisterView.as_view(), name="register"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("lucky_receipt.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
