from django.urls import path, include
from .views import (
    CustomerCreateWebhook,
    CustomerSyncWebhook,
    CustomerDeleteWebhook,
    ProductCreateWebhook,
    ProductSyncWebhook,
    ProductDeleteWebhook,
    SubscriptionCreateWebhook,
    SubscriptionSyncWebhook,
    SubscriptionDeleteWebhook,
)

urlpatterns = [
    path("customer-create-webhook/", CustomerCreateWebhook.as_view()),
    path("customer-sync-webhook/", CustomerSyncWebhook.as_view()),
    path("customer-delete-webhook/", CustomerDeleteWebhook.as_view()),
    path("product-create-webhook/", ProductCreateWebhook.as_view()),
    path("product-sync-webhook/", ProductSyncWebhook.as_view()),
    path("product-delete-webhook/", ProductDeleteWebhook.as_view()),
    path("subscription-create-webhook/", SubscriptionCreateWebhook.as_view()),
    path("subscription-sync-webhook/", SubscriptionSyncWebhook.as_view()),
    path("subscription-delete-webhook/", SubscriptionDeleteWebhook.as_view()),
]
