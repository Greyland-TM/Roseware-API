from apps.accounts.models import Customer
from apps.package_manager.models import (ServicePackage, ServicePackageTemplate)
from apps.stripe.models import StripeSubscription
from apps.stripe.tasks import sync_stripe
from apps.accounts.models import Employee
from .account_setup import get_pipedrive_oauth_tokens
import base64
import json
import requests
import boto3
import requests
import logging
import stripe
import os

logger = logging.getLogger(__name__)

""" CREATE CUSTOMER IN PIPEDRIVE """


def create_pipedrive_customer(customer):
    try:
        # Create the customer in Pipedrive
        # If the owner of the customer is a staff member, use the API key
        # Otherwise, use the OAuth token
        
        headers = None
        if customer.owner.is_staff:
            pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
            pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/persons?api_token={pipedrive_key}"
            pipedrive_person_stripe_url_key = os.environ.get(
                "PIPEDRIVE_PERSON_STRIPE_URL_KEY"
            )
        else:
            pipedrive_person_stripe_url_key = customer.PIPEDRIVE_PERSON_STRIPE_URL_KEY
            pipedrive_domain = customer.piprdrive_api_url
            url = f"{pipedrive_domain}/v1/persons"
            tokens = get_pipedrive_oauth_tokens(customer.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }

        # Create the url that will be used to link the customer to Stripe
        environment = os.environ.get("DJANGO_ENV")
        if environment == "production":
            stripe_url = (
                f"https://dashboard.stripe.com/customers/{customer.stripe_customer_id}"
            )
        else:
            stripe_url = f"https://dashboard.stripe.com/test/customers/{customer.stripe_customer_id}"

        # Make the request to create the customer in Pipedrive
        body = {
            "name": f"{customer.first_name} {customer.last_name}",
            "email": f"{customer.email}",
            "phone": f"{customer.phone}",
            pipedrive_person_stripe_url_key: stripe_url,
        }

        if headers:
            response = requests.post(url, json=body, headers=headers)
        else:
            response = requests.post(url, json=body)

        # Check the response data and update the customers pipedrive id
        data = response.json()
        customer_created = data["success"]

        if not customer_created:
            logger.warning(f"\nCUSTOMER NOT CREATED IN PIPEDRIVE: {data}")
            return False
        pipedrive_customer_id = data["data"]["id"]
        customer.pipedrive_id = pipedrive_customer_id
        customer.save(should_sync_stripe=False, should_sync_pipedrive=False)
        return pipedrive_customer_id
    except Exception as e:
        logger.error(e)
        return False


""" UPDATE CUSTOMER IN PIPEDRIVE """


def update_pipedrive_customer(customer):
    try:
        # Create the customer in Pipedrive
        # If the owner of the customer is a staff member, use the API key
        # Otherwise, use the OAuth token
        headers = None
        if customer.owner.is_staff:
            pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
            pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/persons/{customer.pipedrive_id}?api_token={pipedrive_key}"
            pipedrive_person_stripe_url_key = os.environ.get(
                "PIPEDRIVE_PERSON_STRIPE_URL_KEY"
            )
        else:
            pipedrive_person_stripe_url_key = customer.PIPEDRIVE_PERSON_STRIPE_URL_KEY
            pipedrive_domain = customer.piprdrive_api_url
            url = f"{pipedrive_domain}/v1/persons{customer.pipedrive_id}"
            tokens = get_pipedrive_oauth_tokens(customer.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }

        # Create the url that will be used to link the customer to Stripe
        environment = os.environ.get("DJANGO_ENV")
        if environment == "production":
            stripe_url = (
                f"https://dashboard.stripe.com/customers/{customer.stripe_customer_id}"
            )
        else:
            stripe_url = f"https://dashboard.stripe.com/test/customers/{customer.stripe_customer_id}"

        # Make the request to create the customer in Pipedrive
        body = {
            "name": f"{customer.first_name} {customer.last_name}",
            "email": f"{customer.email}",
            "phone": f"{customer.phone}",
            pipedrive_person_stripe_url_key: stripe_url,
        }
        if headers:
            response = requests.put(url, json=body, headers=headers)
        else:
            response = requests.put(url, json=body)

        data = response.json()
        was_updated = data["success"]
        if not was_updated:
            logger.warning(f"\nCUSTOMER NOT UPDATED IN PIPEDRIVE: {data}")
            return False

        return was_updated
    except Exception as e:
        logger.error(f"Failed with error: {e}")
        return False


""" DELETE CUSTOMER IN PIPEDRIVE """


def delete_pipedrive_customer(pipedrive_id, owner):
    from apps.accounts.models import Customer

    try:
        # Delete the pipedrive product from a pipedrve deal
        if owner.is_staff:
            pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
            pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/persons/{pipedrive_id}?api_token={pipedrive_key}"
            response = requests.delete(url)
        else:
            pipedrive_domain = owner.piprdrive_api_url
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/persons/{pipedrive_id}"
            customer = Customer.objects.get(user=owner)
            tokens = get_pipedrive_oauth_tokens(customer.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }
            response = requests.delete(url, headers=headers)

        data = response.json()
        was_deleted = data["success"]

        if not was_deleted:
            logger.warning(f"\nCUSTOMER NOT DELETED IN PIPEDRIVE: {data}")
            return False
        return was_deleted
    except Exception as e:
        logger.error(e)
        return False


""" CREATE LEAD IN PIPEDRIVE """ ""


def create_pipedrive_lead(customer):
    from apps.accounts.models import Customer

    try:
        # Then create the lead in Pipedrive
        pipedrive_customer_id = customer.pipedrive_id
        if pipedrive_customer_id:
            if customer.owner.is_staff:
                pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
                pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
                url = f"https://{pipedrive_domain}.pipedrive.com/v1/leads?api_token={pipedrive_key}"
                body = {
                    "title": f"{customer.first_name} {customer.last_name} lead",
                    "person_id": int(pipedrive_customer_id),
                }
                response = requests.post(url, json=body)

            else:
                pipedrive_domain = Customer.objects.get(
                    user=customer.owner
                ).pipedrive_api_url
                url = f"{pipedrive_domain}/v1/leads"
                body = {
                    "title": f"{customer.first_name} {customer.last_name} lead",
                    "person_id": int(pipedrive_customer_id),
                }
                lead_created = data["success"]
                tokens = get_pipedrive_oauth_tokens(customer.owner.pk)
                headers = {
                    "Authorization": f'Bearer {tokens["access_token"]}',
                }
                response = requests.post(url, json=body, headers=headers)

            data = response.json()
            lead_created = data["success"]
            if not lead_created:
                logger.warning(f"\nLEAD NOT CREATED IN PIPEDRIVE: {data}")
                return False
            return True
        else:
            return False
    except Exception as e:
        logger.error(e)
        return False


""" CREATE PACKAGE IN PIPEDRIVE """


def create_pipedrive_package_template(package):
    try:
        # Update Packeag in Pipedrive
        # If the owner of the package is a staff member, use the API key
        # Otherwise, use the OAuth token
        headers = None
        if package.owner.is_staff:
            pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
            pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/products?api_token={pipedrive_key}"
            pipedrive_product_stripe_url_key = os.environ.get(
                "PIPEDRIVE_PRODUCT_STRIPE_URL_KEY"
            )
        else:
            pipedrive_product_stripe_url_key = package.owner(
                "PIPEDRIVE_PRODUCT_STRIPE_URL_KEY"
            )
            pipedrive_domain = package.owner.piprdrive_api_url
            url = f"{pipedrive_domain}/v1/products"
            tokens = get_pipedrive_oauth_tokens(package.owner.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }

        # Create the url that will be used to link the package to Stripe
        environment = os.environ.get("DJANGO_ENV")
        if environment == "production":
            stripe_url = (
                f"https://dashboard.stripe.com/products/{package.stripe_product_id}"
            )
        else:
            stripe_url = f"https://dashboard.stripe.com/test/products/{package.stripe_product_id}"

        # Make the request to create the package in Pipedrive
        body = {
            "name": package.name,
            "code": str(package.pk),
            "unit": "1",
            "prices": [{"currency": "USD", "price": float(package.cost)}],
            pipedrive_product_stripe_url_key: stripe_url,
        }
        if headers:
            response = requests.post(url, json=body, headers=headers)
        else:
            response = requests.post(url, json=body)
        data = response.json()
        package_created = data["success"]

        # Check the response data and update the packages pipedrive id
        if not package_created:
            logger.warning(f"\nPACKAGE NOT CREATED IN PIPEDRIVE: {data}")
            return False

        pipedrive_package_id = data["data"]["id"]
        package.pipedrive_id = pipedrive_package_id
        package.save(should_sync_stripe=False, should_sync_pipedrive=False)
        return package_created
    except Exception as e:
        logger.error(e)
        return False


""" UPDATE PACKAGE IN PIPEDRIVE """


def update_pipedrive_package_template(package_template):
    try:
        # Update Packeag in Pipedrive
        # If the owner of the package is a staff member, use the API key
        # Otherwise, use the OAuth token
        headers = None
        if package_template.owner.is_staff:
            pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
            pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/products/{package_template.pipedrive_id}?api_token={pipedrive_key}"
            pipedrive_product_stripe_url_key = os.environ.get(
                "PIPEDRIVE_PRODUCT_STRIPE_URL_KEY"
            )
        else:
            pipedrive_product_stripe_url_key = os.environ.get(
                "PIPEDRIVE_PRODUCT_STRIPE_URL_KEY"
            )
            pipedrive_domain = package_template.owner.piprdrive_api_url
            url = f"{pipedrive_domain}/v1/products/{package_template.pipedrive_id}"
            tokens = get_pipedrive_oauth_tokens(package_template.owner.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }

        # Set the stripe url
        environment = os.environ.get("DJANGO_ENV")
        if environment == "production":
            stripe_url = f"https://dashboard.stripe.com/products/{package_template.stripe_product_id}"
        else:
            stripe_url = f"https://dashboard.stripe.com/test/products/{package_template.stripe_product_id}"

        # Make the request
        body = {
            "name": package_template.name,
            "description": package_template.description,
            "code": str(package_template.pk),
            "unit": "1",
            "prices": [{"currency": "USD", "price": float(package_template.cost)}],
            pipedrive_product_stripe_url_key: stripe_url,
        }
        if headers:
            response = requests.put(url, json=body, headers=headers)
        else:
            response = requests.put(url, json=body)

        data = response.json()
        was_updated = data["success"]
        if not was_updated:
            logger.warning(f"\nPACKAGE NOT UPDATED IN PIPEDRIVE: {data}")
            return False

        return was_updated
    except Exception as e:
        logger.error(e)
        return False


""" DELETE PACKAGE IN PIPEDRIVE """


def delete_pipedrive_package_template(pipedrive_id, owner):
    try:
        # Delete the customer in Pipedrive
        if owner.is_staff:
            pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
            pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/products/{pipedrive_id}?api_token={pipedrive_key}"
            response = requests.delete(url)
        else:
            pipedrive_domain = owner.piprdrive_api_url
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/products/{pipedrive_id}"
            customer = Customer.objects.get(user=owner)
            tokens = get_pipedrive_oauth_tokens(customer.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }
            response = requests.delete(url, headers=headers)

        data = response.json()
        was_deleted = data["success"]

        if not was_deleted:
            logger.warning(f"\nPACKAGE NOT DELETED IN PIPEDRIVE: {data}")
            return False

        return was_deleted
    except Exception as e:
        logger.error(e)
        return False


""" CREATE DEAL IN PIPEDRIVE """


def create_pipedrive_deal(package_plan):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
        pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")

        # Check if the customer has a pipedrive id, if not return false
        if not package_plan.customer.pipedrive_id:
            return False

        # Update Packeag in Pipedrive
        # If the owner of the package is a staff member, use the API key
        # Otherwise, use the OAuth token
        headers = None
        if package_plan.owner.is_staff:
            pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
            pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/deals?api_token={pipedrive_key}"
            pipedrive_deal_stripe_url_key = os.environ.get(
                "PIPEDRIVE_DEAL_STRIPE_URL_KEY"
            )
        else:
            pipedrive_deal_stripe_url_key = os.environ.get(
                "PIPEDRIVE_DEAL_STRIPE_URL_KEY"
            )
            pipedrive_domain = package_plan.owner.piprdrive_api_url
            url = f"{pipedrive_domain}/v1/deals"
            tokens = get_pipedrive_oauth_tokens(package_plan.owner.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }

        # Set the stripe url
        environment = os.environ.get("DJANGO_ENV")
        if environment == "production":
            stripe_url = f"https://dashboard.stripe.com/subscriptions/{package_plan.stripe_subscription_id}"
        else:
            stripe_url = f"https://dashboard.stripe.com/test/subscriptions/{package_plan.stripe_subscription_id}"

        # Make the request
        body = {
            "title": package_plan.name,
            "person_id": package_plan.customer.pipedrive_id,
            "status": 'won',
            # "49051a6391f07f3175cb0984b6c3a849429d0555": package_plan.billing_cycle,
            pipedrive_deal_stripe_url_key: stripe_url,
        }
        if headers:
            response = requests.post(url, json=body, headers=headers)
        else:
            response = requests.post(url, json=body)

        # Check the response data and update the packages pipedrive id
        data = response.json()

        deal_created = data["success"]
        if not deal_created:
            logger.warning(f"\nDEAL NOT CREATED IN PIPEDRIVE: {data}")
        if not deal_created:
            return False

        # Save the pipedrive id to the package plan
        pipedrive_deal_id = data["data"]["id"]
        package_plan.pipedrive_id = pipedrive_deal_id
        package_plan.save(should_sync_pipedrive=False)

        return deal_created
    except Exception as e:
        logger.error(e)
        return False


""" UPDATE DEAL IN PIPEDRIVE """


def update_pipedrive_deal(package_plan):
    try:
        # Get the pipedrive customer id
        pipedrive_customer_id = package_plan.customer.pipedrive_id
        # Then update the deal
        if pipedrive_customer_id:
            # Update Packeag in Pipedrive
            # If the owner of the package is a staff member, use the API key
            # Otherwise, use the OAuth token
            headers = None
            if package_plan.owner.is_staff:
                pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
                pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
                url = f"https://{pipedrive_domain}.pipedrive.com/v1/deals/{package_plan.pipedrive_id}?api_token={pipedrive_key}"
                pipedrive_deal_stripe_url_key = os.environ.get(
                    "PIPEDRIVE_DEAL_STRIPE_URL_KEY"
                )
            else:
                pipedrive_deal_stripe_url_key = os.environ.get(
                    "PIPEDRIVE_DEAL_STRIPE_URL_KEY"
                )
                pipedrive_domain = package_plan.owner.piprdrive_api_url
                url = f"{pipedrive_domain}/v1/deals/{package_plan.pipedrive_id}"
                tokens = get_pipedrive_oauth_tokens(package_plan.owner.pk)
                headers = {
                    "Authorization": f'Bearer {tokens["access_token"]}',
                }

            # Set up the stripe url
            environment = os.environ.get("DJANGO_ENV")
            if environment == "production":
                stripe_url = f"https://dashboard.stripe.com/subscriptions/{package_plan.stripe_subscription_id}"
            else:
                stripe_url = f"https://dashboard.stripe.com/test/subscriptions/{package_plan.stripe_subscription_id}"

            # Make the request
            body = {
                "title": package_plan.name,
                "person_id": package_plan.customer.pipedrive_id,
                "status": package_plan.status,
                # "49051a6391f07f3175cb0984b6c3a849429d0555": package_plan.billing_cycle,
                pipedrive_deal_stripe_url_key: stripe_url,
            }
            if headers:
                response = requests.put(url, json=body, headers=headers)
            else:
                response = requests.put(url, json=body)

            # Check the response data
            data = response.json()
            deal_updated = data["success"]
            if not deal_updated:
                logger.warning(f"\nDEAL NOT UPDATED IN PIPEDRIVE: {data}")
                return False

            return True
        else:
            return False
    except Exception as e:
        logger.error(e)
        return False


""" DELETE DEAL IN PIPEDRIVE """


def delete_pipedrive_deal(deal_id, owner):
    try:
        # Delete the deal in Pipedrive
        if owner.is_staff:
            pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
            pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/deals/{deal_id}?api_token={pipedrive_key}"
            response = requests.delete(url)
        else:
            pipedrive_domain = owner.piprdrive_api_url
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/deals/{deal_id}"
            customer = Customer.objects.get(user=owner)
            tokens = get_pipedrive_oauth_tokens(customer.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }
            response = requests.delete(url, headers=headers)

        data = response.json()
        was_deleted = data["success"]

        if not was_deleted:
            logger.warning(f"\nDEAL NOT DELETED IN PIPEDRIVE: {data}")
            return False

        return was_deleted
        package_plan.delete()
    except Exception as e:
        logger.info(e)
        return False


""" ADD PRODUCT TO PIPEDRIVE DEAL """


def create_pipedrive_service_package(service_package):
    try:
        # Delete the pipedrive product from a pipedrve deal
        if service_package.package_plan.owner.is_staff:
            pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
            pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/deals/{service_package.package_plan.pipedrive_id}/products?api_token={pipedrive_key}"
            body = {
                "product_id": int(service_package.package_template.pipedrive_id),
                "item_price": float(service_package.cost),
                "quantity": int(service_package.quantity),
            }
            response = requests.post(url, json=body)
        else:
            pipedrive_domain = service_package.package_plan.owner.piprdrive_api_url
            url = f"https://{pipedrive_domain}.pipedrive.com/v1"
            f"/deals/{service_package.package_plan.pipedrive_id}0{service_package.pipedrive_product_attachment_id}"
            customer = Customer.objects.get(user=service_package.package_plan.owner)
            tokens = get_pipedrive_oauth_tokens(customer.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }
            response = requests.delete(url, json=body, headers=headers)

        data = response.json()
        deal_created = data["success"]

        if not deal_created:
            logger.warning(f"\nPRODUCT NOT ADDED TO DEAL IN PIPEDRIVE: {data}")
            return False

        # Check the response data and update the packages pipedrive id
        pipedrive_product_attachment_id = data["data"]["id"]
        service_package.pipedrive_product_attachment_id = (
            pipedrive_product_attachment_id
        )
        service_package.save(should_sync_pipedrive=False, should_sync_stripe=False)
        return deal_created
    except Exception as e:
        logger.error(e)
        return False


""" UPDATE PRODUCT IN PIPEDRIVE DEAL """


def update_pipedrive_service_package(service_package):
    try:
        # Add a product to a pipedrive deal
        if service_package.package_plan.owner.is_staff:
            try:
                "/v1/deals/{id}/products/{product_attachment_id}"
                pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
                pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
                url = f"https://{pipedrive_domain}/v1/deals/{service_package.package_plan.pipedrive_id}/products/{service_package.pipedrive_product_attachment_id}?api_token={pipedrive_key}"
                body = {
                    "product_id": int(service_package.package_template.pipedrive_id),
                    "item_price": float(service_package.cost),
                    "quantity": int(service_package.quantity),
                }
                response = requests.put(url, json=body)
            except Exception as e:
                print('Failed to update pipedrive service package: ', e)
                return False
        else:
            pipedrive_domain = service_package.package_plan.owner.pipedrive_api_url
            url = f"{pipedrive_domain}/v1"
            f"/deals/{service_package.package_plan.pipedrive_id}"
            f"/products/{service_package.pipedrive_product_attachment_id}"
            body = {
                "product_id": int(service_package.package_template.pipedrive_id),
                "item_price": float(service_package.cost),
                "quantity": int(service_package.quantity),
            }
            response = requests.put(url, json=body)
            customer = Customer.objects.get(user=service_package.package_plan.owner)
            tokens = get_pipedrive_oauth_tokens(customer.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }
            response = requests.delete(url, json=body, headers=headers)

        data = response.json()
        deal_updated = data["success"]

        if not deal_updated:
            logger.warning(f"\nPRODUCT NOT UPDATED IN PIPEDRIVE: {data}")
            return False

        return deal_updated
    except Exception as e:
        logger.error(e)
        return False


""" DELETE PRODUCT IN PIPEDRIVE DEAL """ ""


def delete_pipedrive_service_package(package_plan_pipedrive_id, service_package_pipedrive_id, owner):
    try:
        # Delete the pipedrive product from a pipedrve deal
        if owner.is_staff:
            pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
            pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")
            url = f"https://{pipedrive_domain}.pipedrive.com/v1/deals/{package_plan_pipedrive_id}/products/{service_package_pipedrive_id}?api_token={pipedrive_key}"
            response = requests.delete(url)
        else:
            pipedrive_domain = owner.piprdrive_api_url
            url = f"https://{pipedrive_domain}.pipedrive.com/v1"
            f"/deals/{package_plan_pipedrive_id}/{service_package_pipedrive_id}"
            customer = Customer.objects.get(user=owner)
            tokens = get_pipedrive_oauth_tokens(customer.pk)
            headers = {
                "Authorization": f'Bearer {tokens["access_token"]}',
            }
            response = requests.delete(url, headers=headers)

        data = response.json()
        deal_deleted = data["success"]

        if not deal_deleted:
            logger.warning(f"\nPRODUCT NOT DELETED IN PIPEDRIVE: {data}")
            return False

        return deal_deleted
    except Exception as e:
        print('Failed to delete pipedrive service package: ', e)
        return False
