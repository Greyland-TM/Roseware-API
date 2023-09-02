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
from roseware.utils import make_logger

logger = make_logger(__name__, stream=True)


""" CREATE STRIPE DETAILS """


def create_stripe_account(customer):
    # Create a Stripe Customer
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        response = stripe.Account.create(
            type="standard",
            country="US",
            email=customer.email
        )
        stripe_account_id = response["id"]
        customer.stripe_account_id = stripe_account_id
        customer.save(should_sync_stripe=False, should_sync_pipedrive=False)
        return True
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False


def setup_payment_details(customer, payment_details, package_plan):
    # Create a Stripe Payment Method
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        customer_payment_method = StripePaymentDetails.objects.filter(
            customer=customer
        ).first()

        logger.info("Creating Stripe Payment Method...")
        stripe_payment_method = StripePaymentDetails(
            customer=customer,
            card_number=payment_details["card_number"],
            expiry_month=payment_details["expiry_month"],
            expiry_year=payment_details["expiry_year"],
            cvc=payment_details["cvc"],
        )
        stripe_payment_method.save()

        stripe_subscription = StripeSubscription(
            customer=customer,
            package_plan=package_plan,
            # payment_details=stripe_payment_method
        )
        stripe_subscription.save()
        return stripe_subscription

    except Exception as error:
        logger.error(f"\nError: {error}")
        return False


""" CREATE STRIPE PRODUCT """


def create_stripe_product(product):
    try:
        stripe.api_key = os.environ.get("STRIPE_PRIVATE")
        # Create a Stripe Product
        stripe_product = stripe.Product.create(
            name=product.name,
            description=product.description,
        )
        stripe_product_id = stripe_product["id"]
        product.stripe_product_id = stripe_product_id
        logger.info("chekc #2")
        # Create a Stripe Price
        stripe_price = stripe.Price.create(
            unit_amount=int(product.cost * 100),
            currency="usd",
            recurring={"interval": "month"},
            product=stripe_product_id,
        )
        logger.info("chekc #3")
        stripe_price_id = stripe_price["id"]
        product.stripe_price_id = stripe_price_id
        product.save(should_sync_stripe=False, should_sync_pipedrive=True)
        return True
    except Exception as error:
        logger.error(f"\nError 1: {error}")
        return False


""" UPDATE STRIPE PRODUCT """


def update_stripe_product(product):
    try:
        stripe.api_key = os.environ.get("STRIPE_PRIVATE")
        # Check the current value of the Stripe Price
        stripe_price = stripe.Price.retrieve(product.stripe_price_id)

        # if the stripe price is NOT the same as the product cost, create a new price
        if int(stripe_price["unit_amount"]) != int(product.cost * 100):
            # Deactivate the old price
            stripe.Price.modify(product.stripe_price_id, active=False)

            # Update a Stripe Price
            stripe_price = stripe.Price.create(
                unit_amount=int(product.cost * 100),
                currency="usd",
                recurring={"interval": "month"},
                product=product.stripe_product_id,
            )
            stripe_price_id = stripe_price["id"]
            product.stripe_price_id = stripe_price_id
            product.save(should_sync_stripe=False, should_sync_pipedrive=False)

        # Update a Stripe Product
        stripe.Product.modify(
            product.stripe_product_id,
            name=product.name,
            description=product.description,
        )
        return True
    except Exception as error:
        logger.error(f"\nError 2: {error}")
        return False


""" DELETE STRIPE PRODUCT """


def delete_stripe_product(stripe_id):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        stripe.Product.modify(stripe_id, active=False)
        return True
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False


""" CREATE STRIPE CUSTOMER """


def create_stripe_customer(customer):
    import traceback

    try:
        stripe.api_key = os.environ.get("STRIPE_PRIVATE")
        if not stripe.api_key:
            logger.info("STRIPE_PRIVATE environment variable not set.")
            return False

        # Create a Stripe Customer
        name = f"{customer.first_name} {customer.last_name}"
        stripe_customer = stripe.Customer.create(
            name=name,
            email=customer.email,
            phone=customer.phone,
        )
        stripe_customer_id = stripe_customer["id"]
        if not stripe_customer_id:
            logger.warning("Could not get customer ID from Stripe.")
            return False

        customer.stripe_customer_id = stripe_customer_id
        customer.save(should_sync_stripe=False)
        return True
    except Exception as error:
        logger.error(f"Error: {error}")
        traceback.logger.info_exc()
        return False


""" UPDATE STRIPE CUSTOMER """


def update_stripe_customer(customer):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        # Update a Stripe Customer
        name = f"{customer.first_name} {customer.last_name}"
        stripe.Customer.modify(
            customer.stripe_customer_id,
            name=name,
            email=customer.email,
            phone=customer.phone,
        )
        return True
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False


""" DELETE STRIPE CUSTOMER """ ""


def delete_stripe_customer(stripe_id):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        # Delete the Stripe Customer
        stripe.Customer.delete(stripe_id)
        return True
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False


""" CREATE STRIPE PAYMENT METHOD """


def create_stripe_payment_method(payment_details):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        # Create a Stripe Payment Method
        stripe_payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": payment_details.card_number,
                "exp_month": payment_details.expiry_month,
                "exp_year": payment_details.expiry_year,
                "cvc": payment_details.cvc,
            },
        )
        stripe_card_id = stripe_payment_method["id"]
        payment_details.stripe_card_id = stripe_card_id
        payment_details.save(should_sync_stripe=False)

        # Attach the Payment Method to the Customer
        stripe.PaymentMethod.attach(
            stripe_card_id,
            customer=payment_details.customer.stripe_customer_id,
        )

        # Set the default payment method on the customer
        stripe.Customer.modify(
            payment_details.customer.stripe_customer_id,
            invoice_settings={"default_payment_method": stripe_card_id},
        )
        return True
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False


""" UPDATE STRIPE PAYMENT METHOD """


def update_stripe_payment_method(payment_details):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        # Update a Stripe Payment Method
        stripe.PaymentMethod.modify(
            payment_details.stripe_payment_method_id,
            card={
                "number": payment_details.card_number,
                "exp_month": payment_details.exp_month,
                "exp_year": payment_details.exp_year,
                "cvc": payment_details.cvc,
            },
        )
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False


""" DELETE STRIPE PAYMENT METHOD """


def delete_stripe_payment_method(stripe_id):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        # Delete the Stripe Payment Method
        stripe.PaymentMethod.detach(stripe_id)
        return True
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False


""" CREATE STRIPE SUBSCRIPTION """


def create_stripe_subscription(subscription):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        # logger.info('Creating Stripe Subscription...')
        # Get all packages associated with the package plan
        package_plan = subscription.package_plan
        service_packages = ServicePackage.objects.filter(package_plan=package_plan)
        # logger.info(f'Found {len(service_packages)} service packages for {package_plan.name}...')
        # Add the subscription item to the list of items for the subscription
        customer = subscription.customer
        items = []
        for service_package in service_packages:
            # Create a Stripe Price
            new_stripe_subscription_item_price = stripe.Price.create(
                unit_amount=int(service_package.cost * 100),
                currency="usd",
                recurring={"interval": "month"},
                product=service_package.package_template.stripe_product_id,
            )
            service_package.stripe_subscription_item_price_id = (
                new_stripe_subscription_item_price["id"]
            )
            service_package.save(should_sync_stripe=False, should_sync_pipedrive=False)

            items.append(
                {
                    "price": new_stripe_subscription_item_price["id"],
                    "quantity": service_package.quantity,
                }
            )

        # Create a subscription on Stripe
        new_subscription = stripe.Subscription.create(
            customer=customer.stripe_customer_id,
            items=items,
            collection_method="charge_automatically",
            # off_session=off_session,
        )
        subscription_id = new_subscription["id"]

        subscription.stripe_subscription_id = subscription_id
        package_plan.stripe_subscription_id = subscription_id
        subscription.save(should_sync_stripe=False)
        package_plan.save(should_sync_stripe=False, should_sync_pipedrive=True)

        # save the subscription item id and price id to the ServicePackage
        data = new_subscription["items"]["data"]
        for service_package in service_packages:
            for item in data:
                if (
                    item["price"]["id"]
                    == service_package.stripe_subscription_item_price_id
                ):
                    service_package.stripe_subscription_item_id = item["id"]
                    service_package.save(
                        should_sync_stripe=False, should_sync_pipedrive=False
                    )

        return subscription
    except stripe.error.StripeError as error:
        logger.error(f"\nError: {error}")
        return None


""" UPDATE STRIPE SUBSCRIPTION """


def update_stripe_subscription(subscription):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")

    def create_new_subscription_price(subscription, service_package):
        if not service_package.stripe_subscription_item_id:
            # logger.warning('No Stripe Subscription Item ID found...')
            return False

        # Check if the prices are the same
        if service_package.stripe_subscription_item_price_id:
            price = stripe.Price.retrieve(
                service_package.stripe_subscription_item_price_id
            )
            current_price = price["unit_amount"]
            new_price = int(service_package.cost * 100)
            are_same_price = current_price == new_price
            # logger.info(f'Current Price: {current_price}, New Price: {new_price}')
            if are_same_price:
                # logger.warning('Prices are the same, no need to update...')
                return False

        # Create a Stripe Price
        # logger.info('Creating new Stripe Price...')
        new_stripe_subscription_item_price = stripe.Price.create(
            unit_amount=int(service_package.cost * 100),
            currency="usd",
            recurring={"interval": "month"},
            product=service_package.package_template.stripe_product_id,
            metadata={"subscription_id": subscription.id},
        )
        # logger.info(f'Created new price: {new_stripe_subscription_item_price}')

        service_package.stripe_subscription_item_price_id = (
            new_stripe_subscription_item_price["id"]
        )
        service_package.save(should_sync_stripe=False, should_sync_pipedrive=False)

        # logger.info('Updating Stripe Subscription Item...')
        # # Update the SubscriptionItem in Stripe
        if service_package.stripe_subscription_item_id:
            subscription_item = stripe.SubscriptionItem.modify(
                service_package.stripe_subscription_item_id,
                quantity=service_package.quantity,
                price=new_stripe_subscription_item_price["id"],
            )
            return subscription_item

    try:
        # Get the PackagePlan associated with the Subscription
        package_plan = subscription.package_plan

        # Get the ServicePackages associated with the PackagePlan
        service_packages = ServicePackage.objects.filter(package_plan=package_plan)

        # Loop through each ServicePackage and create new prices
        # logger.info('Creating Stripe Subscription Items...')
        for service_package in service_packages:
            # If the price exists, store the old price id
            # logger.info('Checking if the price exists...')
            old_price_id = None
            if service_package.stripe_subscription_item_id:
                old_price_id = service_package.stripe_subscription_item_price_id

            # Create a new price, returns false if the price is the same in stripe
            new_subscription_item = create_new_subscription_price(
                subscription, service_package
            )
            # logger.info(f'new_subscription_item: {new_subscription_item}')
            if not new_subscription_item:
                continue

            # logger.info('Deleting old price..')
            if old_price_id and new_subscription_item:
                # logger.info('Deactivating old Stripe Subscription Item Price...')
                # Deactivate the old subscription item price
                modified_price = stripe.Price.modify(
                    old_price_id,
                    active=False,
                )

        # logger.info('Getting all Stripe Subscription ...')
        stripe_items = stripe.SubscriptionItem.list(
            subscription=subscription.stripe_subscription_id
        )
        stripe_ids = [item["id"] for item in stripe_items["data"]]
        # logger.info(f'stripe_ids: {stripe_ids}')

        # Get all the subscription items associated with the ServicePackages
        # logger.info('Get service Packages...')
        service_packages = ServicePackage.objects.filter(package_plan=package_plan)
        service_package_ids = list(
            service_packages.values_list("stripe_subscription_item_id", flat=True)
        )
        # logger.info(f'\nstripe_ids: {stripe_ids}')
        # logger.info(f'service_package_ids: {service_package_ids}')

        for service_package in service_packages:
            if service_package.stripe_subscription_item_id:
                if service_package.stripe_subscription_item_id not in stripe_ids:
                    stripe.SubscriptionItem.delete(
                        service_package.stripe_subscription_item_id
                    )
            else:
                # Create a Stripe Price
                new_stripe_subscription_item_price = stripe.Price.create(
                    unit_amount=int(service_package.cost * 100),
                    currency="usd",
                    recurring={"interval": "month"},
                    product=service_package.package_template.stripe_product_id,
                )
                service_package.stripe_subscription_item_price_id = (
                    new_stripe_subscription_item_price["id"]
                )
                service_package.save(
                    should_sync_stripe=False, should_sync_pipedrive=False
                )

                subscription_item = stripe.SubscriptionItem.create(
                    subscription=subscription.stripe_subscription_id,
                    price=new_stripe_subscription_item_price["id"],
                    quantity=service_package.quantity,
                )

                service_package.stripe_subscription_item_id = subscription_item["id"]
                service_package.save(
                    should_sync_stripe=False, should_sync_pipedrive=False
                )

        for stripe_id in stripe_ids:
            if stripe_id not in service_package_ids:
                # logger.info(f'Deleting Stripe Subscription Item: {stripe_id}')
                stripe.SubscriptionItem.delete(stripe_id)

        return True
    except stripe.error.StripeError as e:
        logger.error(f"Error: {e}")
        return None


""" DELETE STRIPE SUBSCRIPTION """


def delete_stripe_subscription(stripe_id):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        # Delete the Stripe Subscription
        logger.info("\n* DELETING STRIPE SUBSCRIPTION")
        stripe.Subscription.delete(stripe_id)
        return True
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False
