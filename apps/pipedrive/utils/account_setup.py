from apps.accounts.models import Customer
from apps.package_manager.models import (ServicePackage, ServicePackageTemplate)
from apps.stripe.models import StripeSubscription
from apps.stripe.tasks import sync_stripe
from apps.accounts.models import Employee
import base64
import json
import requests
import boto3
import requests
import logging
import stripe
import os

logger = logging.getLogger(__name__)

# --- Pipedrive Oauth Tokens ---
def get_pipedrive_oauth_tokens(customer_pk):
    """
    This function retrieves a customers Pipedrive Oauth tokens from AWS Secrets
    """

    # Initialize the AWS Secrets Manager client
    secret_name = "roseware-secrets"
    region_name = "us-east-2"
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    # Get the access and refresh tokens
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        logger.error("Error retrieving tokens: ", e)
        return False

    env = os.environ.get("DJANGO_ENV")
    secrets = json.loads(response["SecretString"])
    access_token = secrets["roseware-secrets"][env]["oauth-tokens"][str(customer_pk)][
        "access_token"
    ]
    refresh_token = secrets["roseware-secrets"][env]["oauth-tokens"][str(customer_pk)][
        "refresh_token"
    ]

    return {"access_token": access_token, "refresh_token": refresh_token}


# --- Pipedrive Deal Oauth Token Creation ---
def set_pipedrive_keys(customer_pk, access_token, refresh_token):
    """
    This function sets the Pipedrive Oauth tokens in AWS Secrets
    """

    # Create a Secrets Manager client
    secret_name = "roseware-secrets"
    region_name = "us-east-2"
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    env = os.environ.get("DJANGO_ENV")
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    secret_dict = json.loads(get_secret_value_response["SecretString"])
    oauth_tokens = secret_dict["roseware-secrets"][env]["oauth-tokens"]
    customer_key = str(customer_pk)
    if customer_key in oauth_tokens:
        logger.warning(
            f"Credentials for customer {customer_key} already exist. Overwriting."
        )

    # Set the tokens in AWS Secrets Manager
    oauth_tokens[customer_key] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
    client.update_secret(
        SecretId=secret_name,
        SecretString=json.dumps(secret_dict),
    )


# --- Pipedrive Deal Oauth Token Refresh ---
def refresh_pipedrive_tokens(customer_pk, refresh_token):
    """
    This function refreshes the Pipedrive Oauth tokens
    """

    try:
        client_id = os.environ.get("PIPEDRIVE_CLIENT_ID")
        client_secret = os.environ.get("PIPEDRIVE_CLIENT_SECRET")
        authorization_string = f"{client_id}:{client_secret}"
        base64_bytes = base64.b64encode(authorization_string.encode())
        url = "https://oauth.pipedrive.com/oauth/token"
        body = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        headers = {
            "Authorization": "Basic " + base64_bytes.decode(),
        }
        response = requests.post(url, data=body, headers=headers)
        data = response.json()
        set_pipedrive_keys(customer_pk, data["access_token"], data["refresh_token"])
        logger.info("Refreshed tokens successfully!")
        return data
    except Exception as error:
        logger.error(error)
        return False
    

def create_pipedrive_stripe_url_fields(customer_pk):
    """THIS CODE WORKS FOR SETTING ALL THE STRIPE URL FIELDS"""
    try:
        customer = Customer.objects.get(pk=customer_pk)
        pipedrive_domain = customer.piprdrive_api_url
        data = {"name": "stripe url", "field_type": "varchar"}

        tokens = get_pipedrive_oauth_tokens(customer_pk)
        headers = {
            "Authorization": f'Bearer {tokens["access_token"]}',
        }

        try:
            # Add stripe_url field to dealFields
            url = f"{pipedrive_domain}/v1/dealFields"
            response = requests.post(url, data, headers=headers)
            deal_key = response.json()["data"]["key"]

            # Add stripe_url field to personFields
            url = f"{pipedrive_domain}/v1/personFields"
            response = requests.post(url, data=data, headers=headers)
            person_key = response.json()["data"]["key"]

            # Add stripe_url field to productFields
            url = f"{pipedrive_domain}/v1/productFields"
            response = requests.post(url, data=data, headers=headers)
            product_key = response.json()["data"]["key"]
        except Exception as error:
            logger.error("Error creating custom fields: ", error)
            return False

        # Log the keys
        customer.PIPEDRIVE_PERSON_STRIPE_URL_KEY = person_key
        customer.PIPEDRIVE_DEAL_STRIPE_URL_KEY = deal_key
        customer.PIPEDRIVE_PRODUCT_STRIPE_URL_KEY = product_key
        customer.save(should_sync_stripe=False, should_sync_pipedrive=False)
        logger.info("Created stripe url fields in pipedrive successfully!")

    except Exception as error:
        logger.error(f"Failed to create custom fields: {error}")
        return
    

def create_pipedrive_type_fields(customer_pk):
    """THIS CODE CREATES ALL OF THE PIPEFDRIVE CUSTOM FIELDS"""

    try:
        # pipedrive_api_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
        customer = Customer.objects.get(pk=customer_pk)

        # Setup the pipedrive_field_data array that will be used for making the new fields
        choices = ["Subscription", "One Time"]
        statuses = ["Invoice Approval", "Process Immediately"]
        options_choices = [{"label": choice, "active": True} for choice in choices]
        options_statuses = [{"label": status, "active": True} for status in statuses]
        payment_label = "Payment Selection"
        processing_label = "Processing Selection"
        pipedrive_field_data = [
            {"name": payment_label, "field_type": "enum", "options": options_choices},
            {
                "name": processing_label,
                "field_type": "enum",
                "options": options_statuses,
            },
        ]

        # Initialize the AWS Secrets Manager client
        secret_name = "roseware-secrets"
        region_name = "us-east-2"
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region_name)

        # Get the access and refresh tokens
        try:
            response = client.get_secret_value(SecretId=secret_name)
        except Exception as e:
            logger.error("Error retrieving tokens: ", e)
            return False

        env = os.environ.get("DJANGO_ENV")
        secrets = json.loads(response["SecretString"])
        access_token = secrets["roseware-secrets"][env]["oauth-tokens"][
            str(customer_pk)
        ]["access_token"]
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        url = f"https://{pipedrive_domain}.pipedrive.com/v1/dealFields"

        # Create the new fields in pipedrive
        for field in pipedrive_field_data:
            response = requests.post(url, json=field, headers=headers)
            data = response.json()
            if not data["success"] or data["success"] == False:
                return False
            field_id = data["data"]["id"]
            field_name = data["data"]["name"]

            # Make the newly create fields visable and reauired in pipedreive
            if field_id:
                headers = {
                    "Authorization": f"Bearer {access_token}",
                }
                update_url = (
                    f"https://{pipedrive_domain}.pipedrive.com/v1/dealFields/{field_id}"
                )
                update_data = {
                    "add_visible_flag": True,
                    "visible_to": [1],  # 1 represents the Deals section
                    "is_required": True,
                }
                requests.put(update_url, json=update_data)

            # Save the customer
            options = data["data"]["options"]
            if field_name == payment_label:
                customer.PIPEDRIVE_DEAL_TYPE_FIELD = str(field_id)
            elif field_name == processing_label:
                customer.PIPEDRIVE_DEAL_PROCESSING_FIELD = str(field_id)
            for option in options:
                option_label = option["label"]
                option_id = option["id"]
                if option_label == "Subscription":
                    subscription_option_id = option_id
                    customer.PIPEDRIVE_DEAL_SUBSCRIPTION_SELECTOR = str(
                        subscription_option_id
                    )
                elif option_label == "One Time":
                    one_time_option_id = option_id
                    customer.PIPEDRIVE_DEAL_PAYOUT_SELECTOR = str(one_time_option_id)
                elif option_label == "Invoice Approval":
                    invoice_approval_option_id = option_id
                    customer.PIPEDRIVE_DEAL_INVOICE_SELECTOR = str(
                        invoice_approval_option_id
                    )
                elif option_label == "Process Immediately":
                    process_immediately_option_id = option_id
                    customer.PIPEDRIVE_DEAL_PROCESS_NOW_SELECTOR = str(
                        process_immediately_option_id
                    )
                else:
                    print('\nNot saved to customer...\n')

        customer.save(should_sync_stripe=False, should_sync_pipedrive=False)
        logger.info("Saved the option ids to the customer successfully!")
        return True

    except Exception as error:
        logger.error(f"Failed to create custom fields: {error}")
        return False
    

def create_pipedrive_webhooks(access_token=None, customer=None):
    try:
        logger.info("*** Setting Up New Pipedrive Webhooks***")

        # Get the environment variables
        pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
        pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
        pipedrive_user_id = os.environ.get("PIPEDRIVE_USER_ID")
        backend_url = os.environ.get("BACKEND_URL")
        http_auth_user = os.environ.get("HTTP_AUTH_USER")
        http_auth_pass = os.environ.get("HTTP_AUTH_PASSWORD")
        current_webhooks = None

        logger.info("Setting up webhooks...")
        if not access_token:
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/webhooks?api_token={pipedrive_key}"
            current_webhooks_request = requests.get(url)
            current_webhooks = current_webhooks_request.json()["data"]
        else:
            try:
                url = f"https://{pipedrive_domain}.pipedrive.com/v1/webhooks"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                }
                current_webhooks_request = requests.get(url, headers=headers)
                current_webhooks = current_webhooks_request.json()["data"]
            except Exception as e:
                logger.error(f"\n* ERROR CREATING WEBHOOKS: {e}\n")

        # Delete all current webhooks
        logger.info("Deleting current webhooks...")
        for webhook in current_webhooks:
            if not access_token:
                url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks/{webhook["id"]}?api_token={pipedrive_key}'
                requests.delete(url)
            else:
                try:
                    url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks/{webhook["id"]}'
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                    }
                    requests.delete(url, headers=headers)
                except Exception as e:
                    logger.error(f"\n* ERROR CREATING WEBHOOKS: {e}\n")

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
        logger.info("Creating new webhooks...")
        for url_path, object_type, event_action in urls:
            if customer and customer.pk:
                url = f"{backend_url}/{url_path}?pk={customer.pk}"
            else:
                url = f"{backend_url}/{url_path}"

            # Construct the webhook data
            data = {
                "subscription_url": url,
                "event_action": event_action,
                "event_object": object_type,
                "user_id": pipedrive_user_id,
                "http_auth_user": http_auth_user,
                "http_auth_password": http_auth_pass,
                "headers": {"X-Webhook-Secret-Token": webhook_secret_token},
            }

            # Send the webhook creation request
            if not access_token:
                url = f"https://{pipedrive_domain}.pipedrive.com/v1/webhooks?api_token={pipedrive_key}"
                response = requests.post(url, data=data)
                data = response.json()
            else:
                try:
                    url = f"https://{pipedrive_domain}.pipedrive.com/v1/webhooks"
                    headers = {
                        "Authorization": f"Bearer {access_token}"
                        if access_token
                        else f"Bearer {pipedrive_key}",
                    }
                    response = requests.post(url, headers=headers, data=data)
                    data = response.json()
                    # logger.info(f'\n\n### WEBHOOK RESPONSE: {data}\n\n')
                except Exception as e:
                    logger.error(f"\n* ERROR CREATING WEBHOOKS: {e}\n")

            status = data["status"]
            if status == "error":
                logger.info(f"{status}: {data}")
            else:
                logger.info(status)

        logger.info("done")
    except Exception as error:
        logger.error(f"\n* WEBHOOKS FAILED WITH ERROR: {error}\n")


def get_user_tokens(customer_pk):
    try:
        secret_name = "roseware-secrets"
        region_name = "us-east-2"

        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region_name)

        env = os.environ.get("DJANGO_ENV")
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret_dict = json.loads(get_secret_value_response["SecretString"])
        oauth_tokens = secret_dict["roseware-secrets"][env]["oauth-tokens"]
        customer_key = str(customer_pk)

        if customer_key in oauth_tokens:
            user_tokens = oauth_tokens[customer_key]
            return user_tokens  # This will return a dictionary with access_token and refresh_token

        else:
            logger.warning(f"No stored tokens found for customer {customer_key}.")
            return None

    except Exception as e:
        # Handle exceptions thrown by the AWS SDK for Python
        logger.error("Error: ", e)
        return None