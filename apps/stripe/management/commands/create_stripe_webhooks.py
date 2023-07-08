import os

import requests
import stripe
from django.core.management.base import BaseCommand
from django.urls import get_resolver


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            print("*** Setting Up New Stripe Webhooks***")
            # Get the environment variables
            backend_url = os.environ.get('BACKEND_URL')
            stripe.api_key = os.environ.get('STRIPE_PRIVATE')

            # Delete all current webhooks
            print("Getting current webhooks...")
            current_webhooks = stripe.WebhookEndpoint.list()

            # Delete all current webhooks
            print("Deleting current webhooks...")
            for webhook in current_webhooks:
                stripe.WebhookEndpoint.delete(webhook.id)

            # Set the webhook urls
            webhook_urls = [
                ("customer-create-webhook/", "customer.created", "STRIPE_CUSTOMER_CREAT_WEBHOOK_SECRET"),
                ("customer-sync-webhook/", "customer.updated", "STRIPE_CUSTOMER_SYNC_WEBHOOK_SECRET"),
                ("customer-delete-webhook/", "customer.deleted", "STRIPE_CUSTOMER_DELETE_WEBHOOK_SECRET"),
                ("product-create-webhook/", "product.created", "STRIPE_PRODUCT_CREATE_WEBHOOK_SECRET"),
                ("product-sync-webhook/", "product.updated", "STRIPE_PRODUCT_SYNC_WEBHOOK_SECRET"),
                ("product-delete-webhook/", "product.deleted", "STRIPE_PRODUCT_DELETE_WEBHOOK_SECRET"),
                ("subscription-create-webhook/", "customer.subscription.created", "STRIPE_SUBSCRIPTION_CREATE_WEBHOOK_SECRET"),
                ("subscription-sync-webhook/", "customer.subscription.updated", "STRIPE_SUBSCRIPTION_SYNC_WEBHOOK_SECRET"),
                ("subscription-delete-webhook/", "customer.subscription.deleted", "STRIPE_SUBSCRIPTION_DELETE_WEBHOOK_SECRET"),
            ]
            
            # Get the environment variables
            webhook_secret_token = os.environ.get("WEBHOOK_SECRET_TOKEN")

            # Create new webhooks
            print("Creating new webhooks...")
            for url_path, event, key_name in webhook_urls:
                url = f"{backend_url}/stripe/{url_path}"
                print(url)

                new_webhook = stripe.WebhookEndpoint.create(
                    url=url,
                    enabled_events=[event],
                    metadata={
                        "X-Webhook-Secret-Token": webhook_secret_token,
                    },
                )
                print(new_webhook["status"])
                
                # Store the signing secret in an environment variable
                try:
                    os.environ[key_name] = new_webhook['secret']
                except Exception as e:
                    print(e)
                
            print("Done!")
        except Exception as e:
            print('Error: ', e)
