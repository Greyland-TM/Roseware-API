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

""" CREATE STRIPE PRODUCT """


def create_stripe_product(product):
    try:
        stripe.api_key = os.environ.get("STRIPE_PRIVATE")
        stripe_account = None
        if not product.owner.is_staff:
            stripe_account = product.owner.stripe_account_id

        # Create a Stripe Product
        stripe_product = stripe.Product.create(
            name=product.name,
            description=product.description,
            stripe_account=stripe_account,
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
            stripe_account=stripe_account,
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
        stripe_account = None
        if not product.owner.is_staff:
            stripe_account = product.owner.stripe_account_id

        # Check the current value of the Stripe Price
        stripe_price = stripe.Price.retrieve(
            product.stripe_price_id, stripe_account=stripe_account
        )

        # if the stripe price is NOT the same as the product cost, create a new price
        if int(stripe_price["unit_amount"]) != int(product.cost * 100):
            # Deactivate the old price
            stripe.Price.modify(
                product.stripe_price_id,
                active=False,
                stripe_account=stripe_account,
            )

            # Update a Stripe Price
            stripe_price = stripe.Price.create(
                unit_amount=int(product.cost * 100),
                currency="usd",
                recurring={"interval": "month"},
                product=product.stripe_product_id,
                stripe_account=stripe_account,
            )
            stripe_price_id = stripe_price["id"]
            product.stripe_price_id = stripe_price_id
            product.save(should_sync_stripe=False, should_sync_pipedrive=False)

        # Update a Stripe Product
        stripe.Product.modify(
            product.stripe_product_id,
            name=product.name,
            description=product.description,
            stripe_account=stripe_account,
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
        stripe_account = None
        if not customer.owner.is_staff:
            stripe_account = customer.stripe_account_id

        # Create a Stripe Customer
        name = f"{customer.first_name} {customer.last_name}"
        stripe_customer = stripe.Customer.create(
            name=name,
            email=customer.email,
            phone=customer.phone,
            stripe_account=stripe_account,
        )
        stripe_customer_id = stripe_customer["id"]
        if not stripe_customer_id:
            logger.warning("Could not get customer ID from Stripe.")
            return False

        customer.stripe_customer_id = stripe_customer_id
        customer.save(should_sync_stripe=False)
        create_stripe_account(customer)
        return True
    except Exception as error:
        logger.error(f"Error: {error}")
        traceback.logger.info_exc()
        return False


""" UPDATE STRIPE CUSTOMER """


def update_stripe_customer(customer):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        stripe_account = None 
        if not customer.owner.is_staff:
            stripe_account = customer.stripe_account_id

        # Update a Stripe Customer
        name = f"{customer.first_name} {customer.last_name}"
        stripe.Customer.modify(
            customer.stripe_customer_id,
            name=name,
            email=customer.email,
            phone=customer.phone,
            stripe_account=stripe_account,
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


def create_stripe_payment_method(payment_details, owner):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        stripe_account = None
        if not owner.is_staff:
            stripe_account = payment_details.stripe_account_id
        # Create a Stripe Payment Method
        stripe_payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": payment_details.card_number,
                "exp_month": payment_details.expiry_month,
                "exp_year": payment_details.expiry_year,
                "cvc": payment_details.cvc,
            },
            stripe_account=stripe_account,
        )
        stripe_card_id = stripe_payment_method["id"]
        payment_details.stripe_card_id = stripe_card_id
        payment_details.save(should_sync_stripe=False)

        # Attach the Payment Method to the Customer
        stripe.PaymentMethod.attach(
            stripe_card_id,
            customer=payment_details.customer.stripe_customer_id,
            stripe_account=stripe_account,
        )

        # Set the default payment method on the customer
        stripe.Customer.modify(
            payment_details.customer.stripe_customer_id,
            invoice_settings={"default_payment_method": stripe_card_id},
            stripe_account=stripe_account,
        )
        return True
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False


""" UPDATE STRIPE PAYMENT METHOD """


def update_stripe_payment_method(payment_details, owner):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        stripe_account = None
        if not owner.is_staff:
            stripe_account = owner.stripe_account_id
        # Update a Stripe Payment Method
        stripe.PaymentMethod.modify(
            payment_details.stripe_payment_method_id,
            card={
                "number": payment_details.card_number,
                "exp_month": payment_details.exp_month,
                "exp_year": payment_details.exp_year,
                "cvc": payment_details.cvc,
            },
            stripe_account=stripe_account,
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


def create_stripe_subscription(subscription, owner):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        # Get the stripe account
        stripe_account = None
        if not owner.is_staff:
            stripe_account = owner.stripe_account_id
        package_plan = subscription.package_plan

        # Get all packages associated with the package plan
        service_packages = ServicePackage.objects.filter(package_plan=package_plan)

        # TODO - This is creating a new price for each subscription. This is not ideal.
        # It is leadin to many prices being created in Stripe. 
        
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
                stripe_account=stripe_account,
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
            stripe_account=stripe_account,
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


def update_stripe_subscription(subscription, owner):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    stripe_account = None
    if not owner.is_staff:
        stripe_account = owner.stripe_account_id
    
    def create_new_subscription_price(subscription, service_package):
        if not service_package.stripe_subscription_item_id:
            # logger.warning('No Stripe Subscription Item ID found...')
            return False

        # Check if the prices are the same
        if service_package.stripe_subscription_item_price_id:
            price = stripe.Price.retrieve(
                service_package.stripe_subscription_item_price_id,
                stripe_account=stripe_account,
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
            stripe_account=stripe_account,
        )
        logger.info(f'Created new price: {new_stripe_subscription_item_price}')

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
                stripe_account=stripe_account,
            )
            return subscription_item

    try:
        # Get the PackagePlan associated with the Subscription
        package_plan = subscription.package_plan
        logger.debug("Package Plan ID:", package_plan.id)
        logger.debug(type(subscription))
        logger.debug("Stripe Subscription ID:", subscription.stripe_subscription_id)


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
                    stripe_account=stripe_account,
                )

        # logger.info('Getting all Stripe Subscription ...')
        stripe_items = stripe.SubscriptionItem.list(
            subscription=subscription.stripe_subscription_id,
            stripe_account=stripe_account,
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
                        service_package.stripe_subscription_item_id,
                        stripe_account=stripe_account,
                    )
            else:
                # Create a Stripe Price
                new_stripe_subscription_item_price = stripe.Price.create(
                    unit_amount=int(service_package.cost * 100),
                    currency="usd",
                    recurring={"interval": "month"},
                    product=service_package.package_template.stripe_product_id,
                    stripe_account=stripe_account,
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
                    stripe_account=stripe_account,
                )

                service_package.stripe_subscription_item_id = subscription_item["id"]
                service_package.save(
                    should_sync_stripe=False, should_sync_pipedrive=False
                )

        for stripe_id in stripe_ids:
            if stripe_id not in service_package_ids:
                # logger.info(f'Deleting Stripe Subscription Item: {stripe_id}')
                stripe.SubscriptionItem.delete(stripe_id, stripe_account=stripe_account)

        return True
    except stripe.error.StripeError as e:
        logger.error(f"Error: {e}")
        return None


""" DELETE STRIPE SUBSCRIPTION """


def delete_stripe_subscription(stripe_id):
    stripe.api_key = os.environ.get("STRIPE_PRIVATE")
    try:
        # Delete the Stripe Subscription
        stripe.Subscription.delete(stripe_id)
        return True
    except Exception as error:
        logger.error(f"\nError: {error}")
        return False
