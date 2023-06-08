from django.urls import path, include
from .views import (
    CustomerCreateWebhook,
    CustomerSyncWebhook,
    CustomerDeleteWebhook,
    PackageCreateWebhook,
    PackageSyncWebhook,
    PackageDeleteWebhook,
    DealCreateWebhook,
    DealSyncWebhook,
    DealDeleteWebhook,
    
)

urlpatterns = [
    path("customer-create-webhook/", CustomerCreateWebhook.as_view()),
    path("customer-sync-webhook/", CustomerSyncWebhook.as_view()),
    path("customer-delete-webhook/", CustomerDeleteWebhook.as_view()),
    path("package-create-webhook/", PackageCreateWebhook.as_view()),
    path("package-sync-webhook/", PackageSyncWebhook.as_view()),
    path("package-delete-webhook/", PackageDeleteWebhook.as_view()),
    path("deal-create-webhook/", DealCreateWebhook.as_view()),
    path("deal-sync-webhook/", DealSyncWebhook.as_view()),
    path("deal-delete-webhook/", DealDeleteWebhook.as_view()),
]