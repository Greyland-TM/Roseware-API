import os
import time

import stripe
from celery.exceptions import Retry

from apps.accounts.models import Customer
from apps.package_manager.models import (
    PackagePlan,
    ServicePackage,
    ServicePackageTemplate,
)
from apps.stripe.models import StripePaymentDetails, StripeSubscription
import logging

logger = logging.getLogger(__name__)

""" CREATE STRIPE DETAILS """


def create_stripe_account(customer):
    # Create a Stripe Customer
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        response = stripe.Account.create(
            type="standard", country="US", email=customer.email
        )
        stripe_account_id = response["id"]
        customer.stripe_account_id = stripe_account_id
        customer.save(should_sync_stripe=False, should_sync_pipedrive=False)
        return True
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False


# def setup_payment_details(customer, payment_details, package_plan):
#     # Create a Stripe Payment Method
#     stripe.api_key = os.environ.get("STRIPE_PRIVATE")
#     try:
#         # customer_payment_method = StripePaymentDetails.objects.filter(
#         #     customer=customer
#         # ).first()

#         logger.info("Creating Stripe Payment Method...")
#         stripe_payment_method = StripePaymentDetails(
#             customer=customer,
#             card_number=payment_details["card_number"],
#             expiry_month=payment_details["expiry_month"],
#             expiry_year=payment_details["expiry_year"],
#             cvc=payment_details["cvc"],
#         )
#         stripe_payment_method.save()

#         stripe_subscription = StripeSubscription(
#             customer=customer,
#             package_plan=package_plan,
#             # payment_details=stripe_payment_method
#         )
#         stripe_subscription.save()
#         return stripe_subscription

#     except Exception as error:
#         logger.error(f"\nError: {error}")
#         return False