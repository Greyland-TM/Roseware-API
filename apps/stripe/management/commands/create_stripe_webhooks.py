import os

import requests
import stripe
from django.core.management.base import BaseCommand
from django.urls import get_resolver
from roseware.utils import make_logger

logger = make_logger(__name__, stream=True)


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            logger.info("*** Setting Up New Stripe Webhooks***")
            # Get the environment variables
            backend_url = os.environ.get("BACKEND_URL")
            stripe.api_key = os.environ.get("STRIPE_PRIVATE")

            # Delete all current webhooks
            logger.info("Getting current webhooks...")
            current_webhooks = stripe.WebhookEndpoint.list()

            # Delete all current webhooks
            logger.info("Deleting current webhooks...")
            for webhook in current_webhooks:
                stripe.WebhookEndpoint.delete(webhook.id)

            # Set the webhook urls
            webhook_urls = [
                (
                    "customer-create-webhook/",
                    "customer.created",
                    "STRIPE_CUSTOMER_CREAT_WEBHOOK_SECRET",
                ),
                (
                    "customer-sync-webhook/",
                    "customer.updated",
                    "STRIPE_CUSTOMER_SYNC_WEBHOOK_SECRET",
                ),
                (
                    "customer-delete-webhook/",
                    "customer.deleted",
                    "STRIPE_CUSTOMER_DELETE_WEBHOOK_SECRET",
                ),
                (
                    "product-create-webhook/",
                    "product.created",
                    "STRIPE_PRODUCT_CREATE_WEBHOOK_SECRET",
                ),
                (
                    "product-sync-webhook/",
                    "product.updated",
                    "STRIPE_PRODUCT_SYNC_WEBHOOK_SECRET",
                ),
                (
                    "product-delete-webhook/",
                    "product.deleted",
                    "STRIPE_PRODUCT_DELETE_WEBHOOK_SECRET",
                ),
                (
                    "subscription-create-webhook/",
                    "customer.subscription.created",
                    "STRIPE_SUBSCRIPTION_CREATE_WEBHOOK_SECRET",
                ),
                (
                    "subscription-sync-webhook/",
                    "customer.subscription.updated",
                    "STRIPE_SUBSCRIPTION_SYNC_WEBHOOK_SECRET",
                ),
                (
                    "subscription-delete-webhook/",
                    "customer.subscription.deleted",
                    "STRIPE_SUBSCRIPTION_DELETE_WEBHOOK_SECRET",
                ),
                (
                    "payment-intent-success-webhook/",
                    "payment_intent.succeeded",
                    "STRIPE_PAYMENT_INTENT_SUCCESS_WEBHOOK_SECRET",
                ),
            ]

            # Get the environment variables
            webhook_secret_token = os.environ.get("WEBHOOK_SECRET_TOKEN")

            # Create new webhooks
            logger.info("Creating new webhooks...")
            for url_path, event, key_name in webhook_urls:
                url = f"{backend_url}/stripe/{url_path}"

                new_webhook = stripe.WebhookEndpoint.create(
                    url=url,
                    enabled_events=[event],
                    metadata={
                        "X-Webhook-Secret-Token": webhook_secret_token,
                    },
                )
                logger.info(new_webhook["status"])

                # Store the signing secret in an environment variable
                try:
                    os.environ[key_name] = new_webhook["secret"]
                except Exception as e:
                    logger.error(e)

            logger.info("Done!")
        except Exception as e:
            logger.error("Error: ", e)
