""" Roseware API URL Configuration """

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("knox.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("package-manager/", include("apps.package_manager.urls")),
    path("pipedrive/", include("apps.pipedrive.urls")),
    path("stripe/", include("apps.stripe.urls")),
]
