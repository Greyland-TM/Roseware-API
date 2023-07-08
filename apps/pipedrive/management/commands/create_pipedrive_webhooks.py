from django.core.management.base import BaseCommand
import os
import requests
from django.urls import get_resolver
import hashlib

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            print("*** Setting Up New Stripe Webhooks***")

            # Get the environment variables
            # environment = os.environ.get('DJANGO_ENV')
            pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
            pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')
            # else:
            #     pipedrive_key = os.environ.get('PIPEDRIVE_STAGING_API_KEY')
            #     pipedrive_domain = os.environ.get('PIPEDRIVE_STAGING_DOMAIN')
            pipedrive_user_id = os.environ.get('PIPEDRIVE_USER_ID')
            backend_url = os.environ.get('BACKEND_URL')
            http_auth_user = os.environ.get('HTTP_AUTH_USER')
            http_auth_pass = os.environ.get('HTTP_AUTH_PASSWORD')

            # Get all current webhooks
            print("Getting current webhooks...")
            url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks?api_token={pipedrive_key}'
            current_webhooks_request = requests.get(url)
            current_webhooks = current_webhooks_request.json()['data']

            # Delete all current webhooks
            print("Deleting current webhooks...")
            for webhook in current_webhooks:
                url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks/{webhook["id"]}?api_token={pipedrive_key}'
                requests.delete(url)

            # Get all urls from ../urls.py
            urls = [
                ("pipedrive/customer-create-webhook/", "person", "added"),
                ("pipedrive/customer-sync-webhook/", "person", "updated"),
                ("pipedrive/customer-delete-webhook/", "person", "deleted"),
                ("pipedrive/deal-create-webhook/", "deal", "added"),
                ("pipedrive/deal-sync-webhook/", "deal", "updated"),
                ("pipedrive/deal-delete-webhook/", "deal", "deleted"),
                ("pipedrive/package-create-webhook/", "product", "added"),
                ("pipedrive/package-sync-webhook/", "product", "updated"),
                ("pipedrive/package-delete-webhook/", "product", "deleted"),
            ]

            # Get the environment variables
            webhook_secret_token = os.environ.get("WEBHOOK_SECRET_TOKEN")

            # Create new webhooks
            print("Creating new webhooks...")
            for url_path, object_type, event_action in urls:
                url = f"{backend_url}/{url_path}"

                # Construct the webhook data
                data = {
                    "subscription_url": url,
                    "event_action": event_action,
                    "event_object": object_type,
                    "user_id": pipedrive_user_id,
                    "http_auth_user": http_auth_user,
                    "http_auth_password": http_auth_pass,
                    "headers": {
                        "X-Webhook-Secret-Token": webhook_secret_token
                    }
                }

                # Send the webhook creation request
                url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks?api_token={pipedrive_key}'
                print(url)
                response = requests.post(url, data=data)
                data = response.json()
                
                status = data['status']
                if status == 'error':
                    print(f'{status}: {data}')
                else:
                    print(status)
         
            print('done')
        except Exception as error:
            print(f'failed with error: {error}')
