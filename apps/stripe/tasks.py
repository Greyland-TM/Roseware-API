from roseware.celery import app
from apps.accounts.models import Customer
from apps.package_manager.models import ServicePackageTemplate, PackagePlan, ServicePackage
from .models import StripePaymentDetails, StripeSubscription
from roseware.utils import make_logger
from .utils import (
    create_stripe_customer,
    update_stripe_customer,
    delete_stripe_customer,
    create_stripe_product,
    update_stripe_product,
    delete_stripe_product,
    create_stripe_payment_method,
    update_stripe_payment_method,
    delete_stripe_payment_method,
    create_stripe_subscription,
    update_stripe_subscription,
    delete_stripe_subscription,
)

logger = make_logger()


@app.task(default_retry_delay=10, max_retries=3, autoretry_for=(Exception, ))
def sync_stripe(pk, action, type):
    logger.info('running sync_stripe')
    try:
        if type == 'customer':

            # *** Create New Stripe Customer ***
            if action == 'create':
                customer = Customer.objects.filter(pk=pk).first()
                was_customer_created = create_stripe_customer(customer)
                if not was_customer_created:
                    logger.error('*** Failed to create customer in Stripe ***')
                return was_customer_created

            # *** Update Existing Stripe Customer ***
            elif action == 'update':
                customer = Customer.objects.filter(pk=pk).first()
                was_customer_updated = update_stripe_customer(customer)
                if not was_customer_updated:
                    logger.error('*** Failed to update customer in Stripe ***')
                return was_customer_updated

            # *** Delete Existing Stripe Customer ***
            elif action == 'delete':
                was_customer_deleted = delete_stripe_customer(pk)
                if not was_customer_deleted:
                    logger.error('*** Failed to delete customer in Stripe ***')
                return was_customer_deleted

        if type == 'package_template':

            # *** Create New Stripe Product ***
            if action == 'create':
                product = ServicePackageTemplate.objects.filter(pk=pk).first()
                was_product_created = create_stripe_product(product)
                if not was_product_created:
                    logger.error('*** Failed to create product in Stripe ***')
                return was_product_created

            # *** Update Existing Stripe Product ***
            elif action == 'update':
                product = ServicePackageTemplate.objects.filter(pk=pk).first()
                was_product_updated = update_stripe_product(product)
                if not was_product_updated:
                    logger.error('*** Failed to update product in Stripe ***')
                return was_product_updated

            # *** Delete Existing Stripe Product ***
            elif action == 'delete':
                was_product_deleted = delete_stripe_product(pk)
                if not was_product_deleted:
                    logger.error('*** Failed to delete product in Stripe ***')
                return was_product_deleted

        if type == 'payment_details':

            # *** Create New Stripe Payment Method ***
            if action == 'create':
                payment_details = StripePaymentDetails.objects.filter(pk=pk).first()
                was_payment_method_created = create_stripe_payment_method(payment_details)
                if not was_payment_method_created:
                    logger.error('*** Failed to create payment method in Stripe ***')
                return was_payment_method_created

            # *** Update Existing Stripe Payment Method ***
            elif action == 'update':
                payment_details = StripePaymentDetails.objects.filter(pk=pk).first()
                was_payment_method_updated = update_stripe_payment_method(payment_details)
                if not was_payment_method_updated:
                    logger.error('*** Failed to update payment method in Stripe ***')
                return was_payment_method_updated

            # *** Delete Existing Stripe Payment Method ***
            elif action == 'delete':
                was_payment_method_deleted = delete_stripe_payment_method(pk)
                if not was_payment_method_deleted:
                    logger.error('*** Failed to delete payment method in Stripe ***')
                return was_payment_method_deleted

        if type == 'subscription':

            # *** Create New Stripe Subscription ***
            if action == 'create':
                subscription = StripeSubscription.objects.filter(pk=pk).first()
                was_subscription_created = create_stripe_subscription(subscription)
                if not was_subscription_created:
                    logger.error('*** Failed to create subscription in Stripe ***')
                return was_subscription_created

            # *** Update Existing Stripe Subscription ***
            elif action == 'update':
                print(f'Updating Stripe Subscription: {pk}')
                subscription = StripeSubscription.objects.filter(pk=pk).first()
                print(f'Subscription: {subscription}')
                was_subscription_updated = update_stripe_subscription(subscription)
                if not was_subscription_updated:
                    logger.error('*** Failed to update subscription in Stripe ***')
                return was_subscription_updated

            # *** Delete Existing Stripe Subscription ***
            elif action == 'delete':
                was_subscription_deleted = delete_stripe_subscription(pk)  # pk is stripe_subscription_id
                if not was_subscription_deleted:
                    logger.error('*** Failed to delete subscription in Stripe ***')
                return was_subscription_deleted

        # if type == 'service_package':

    except Exception as e:
        logger.error(f"\nError: {e}")
        return False
