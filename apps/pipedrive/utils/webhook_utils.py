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


# --- Pipedrive Deal Creation Webhook ---
def create_stripe_subscription_from_pipedrive_webhook(request, deal_products, package_plan):
    """ 
    This function is used in the Pipedrive DealCreateWebhook view. 
    It is called when a new subscrption deal is created in pipedrive for immediate processing.
    It is responsible for setting up the stripe subscription and creating the service packages.
    """

    # Create the service packages
    for product in deal_products:
        pipedrive_product_attachment_id = product["id"]
        service_package = ServicePackage.objects.filter(
            pipedrive_product_attachment_id=pipedrive_product_attachment_id
        ).first()
        if not service_package:
            product_id = product["product_id"]
            package_template = ServicePackageTemplate.objects.filter(
                pipedrive_id=product_id
            ).first()
            service_package = ServicePackage(
                pipedrive_product_attachment_id=pipedrive_product_attachment_id,
                package_plan=package_plan,
                customer=package_plan.customer,
                package_template=package_template,
                cost=product["item_price"],
                quantity=product["quantity"],
            )
            service_package.save(
                should_sync_pipedrive=False, should_sync_stripe=False
            )

    # Check if the customer has a payment method setup in Stripe
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    customer_id = package_plan.customer.stripe_customer_id
    try:
        customer = stripe.Customer.retrieve(customer_id)
        payment_methods = customer["default_source"]
        if len(deal_products) > 0 and not payment_methods:
            package_plan.status = "lost"
            package_plan.save(
                should_sync_pipedrive=True, should_sync_stripe=False
            )
            # TODO - If this response failes here it's because the customer did not have a payment method in stripe,
            # but the user tried to create a subscription in pipedrive. We need to handle this case better. Right now 
            # it sets the deal to 'lost' so that it turns red in pipedrive. But we should add a message somehow. Maybe in pipedrive notes?
            return {
                "ok": True,
                "message": "No payment method found for this customer.",
            }
    except stripe.error.StripeError as e:
        print("Failed while checking for customer payment methods. ", e)
        return {
                "ok": False,
                "message": "Failed to retrieve customer payment methods.",
            }
    logger.info(
        "Creating a new subscription for the customer. Processing now..."
    )
    stripe_subscription = StripeSubscription.objects.filter(
        customer=package_plan.customer
    ).first()

    # If the customer already has a subscription just return true, otherwise create it
    if stripe_subscription:
        subscription_pk = stripe_subscription.pk
        sync_stripe.delay(subscription_pk, "update", "subscription")
        return {"ok": True}
    else:
        customer_pk = request.GET.get("pk")
        if customer_pk is not None:
            customer = Customer.objects.get(pk=customer_pk)
            owner = customer.user
        else:
            employee = Employee.objects.all().first()
            owner = employee.user

        stripe_subscription = StripeSubscription(
            customer=package_plan.customer,
            package_plan=package_plan,
            owner=owner,
        )
        package_plan.status = "won"
        package_plan.save()
        stripe_subscription.save()