from django.contrib import admin
from .models import StripePaymentDetails, StripeSubscription

@admin.register(StripePaymentDetails)
class StripePaymentDetailsAdmin(admin.ModelAdmin):

    # display all
    list_display = [
        "customer",
        "stripe_card_id"
    ]
@admin.register(StripeSubscription)
class StripeSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "customer",
        "package_plan",
        # "payment_details",
        "stripe_subscription_id"
    ]
