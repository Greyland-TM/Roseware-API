from django.db import models
import logging
from apps.accounts.models import CustomUser

logger = logging.getLogger(__name__)


# Create your models here.
class StripePaymentDetails(models.Model):
    customer = models.ForeignKey("accounts.Customer", on_delete=models.CASCADE)
    card_number = models.CharField(max_length=255, blank=True, null=True)
    expiry_month = models.CharField(max_length=255, blank=True, null=True)
    expiry_year = models.CharField(max_length=255, blank=True, null=True)
    cvc = models.CharField(max_length=255, blank=True, null=True)
    card_holder_name = models.CharField(max_length=255, blank=True, null=True)
    card_holder_email = models.CharField(max_length=255, blank=True, null=True)
    card_holder_phone = models.CharField(max_length=255, blank=True, null=True)
    card_holder_address = models.CharField(max_length=255, blank=True, null=True)
    card_holder_city = models.CharField(max_length=255, blank=True, null=True)
    card_holder_state = models.CharField(max_length=255, blank=True, null=True)
    card_holder_zip = models.CharField(max_length=255, blank=True, null=True)
    card_holder_country = models.CharField(max_length=255, blank=True, null=True)
    stripe_card_id = models.CharField(max_length=255, blank=True, null=True)

    def save(self, should_sync_stripe=True, *args, **kwargs):
        from apps.stripe.tasks import sync_stripe

        is_new = self._state.adding
        super(StripePaymentDetails, self).save(*args, **kwargs)

        if should_sync_stripe:
            if is_new:
                logger.info("Creating payment details in Stripe... (Check celery terminal)")
                sync_stripe.apply(
                    kwargs={
                        "pk": self.pk,
                        "action": "create",
                        "type": "payment_details",
                    }
                )
            else:
                logger.info("Updating payment details in Stripe... (Check celery terminal)")
                sync_stripe.delay(
                    kwargs={
                        "pk": self.pk,
                        "action": "update",
                        "type": "payment_details",
                    }
                )

    def delete(self, should_sync_stripe=True, *args, **kwargs):
        from apps.stripe.tasks import sync_stripe

        stripe_id = self.stripe_card_id
        super(StripePaymentDetails, self).delete(*args, **kwargs)

        if should_sync_stripe:
            logger.info("Deleting payment details in Stripe... (Check celery terminal)")
            sync_stripe.delay(
                kwargs={"pk": stripe_id, "action": "delete", "type": "payment_details"}
            )


class StripeSubscription(models.Model):
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="subscription_owner", null=True, blank=True)
    customer = models.ForeignKey("accounts.Customer", on_delete=models.CASCADE)
    package_plan = models.ForeignKey(
        "package_manager.PackagePlan", on_delete=models.CASCADE, blank=True, null=True
    )
    # payment_details = models.ForeignKey('StripePaymentDetails', on_delete=models.CASCADE, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)

    def save(self, should_sync_stripe=True, *args, **kwargs):
        from apps.stripe.tasks import sync_stripe

        is_new = self._state.adding
        super(StripeSubscription, self).save(*args, **kwargs)

        if should_sync_stripe:
            if is_new:
                logger.info("Creating subscription in Stripe... (Check celery terminal)")
                sync_stripe.apply(
                    kwargs={"pk": self.pk, "action": "create", "type": "subscription"}
                )
            else:
                logger.info("Updating subscription in Stripe... (Check celery terminal)")
                sync_stripe.delay(
                    kwargs={"pk": self.pk, "action": "update", "type": "subscription"}
                )

    def delete(self, should_sync_stripe=True, *args, **kwargs):
        from apps.stripe.tasks import sync_stripe

        stripe_id = self.stripe_subscription_id
        super(StripeSubscription, self).delete(*args, **kwargs)

        if should_sync_stripe:
            logger.info("Deleting subscription in Stripe... (Check celery terminal)")
            sync_stripe.delay(stripe_id, "delete", "subscription")
