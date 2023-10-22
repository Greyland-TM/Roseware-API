from .models import ServicePackage, ServicePackageTemplate, PackagePlan
from apps.pipedrive.tasks import sync_pipedrive
from apps.stripe.tasks import sync_stripe
from apps.accounts.utils import update_or_create_ongoing_sync
import logging
from apps.stripe.models import StripeSubscription

logger = logging.getLogger(__name__)


# These functions are called from the .save method of the models.
# Calling them like this allows the tasks to be called in the correct order.
def create_package_template_sync(
    package_template, should_sync_pipedrive, should_sync_stripe, owner
):
    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = package_template.last_synced_from

    # Check for an ongoing sync
    update_or_create_ongoing_sync(
        type="package_template",
        action="create",
        should_sync_stripe=should_sync_stripe,
        should_sync_pipedrive=should_sync_pipedrive,
        sync_platform=sync_platform,
        owner=owner,
    )

    # Start the sync tasks
    if should_sync_pipedrive:
        logger.info("Creating package template in Pipedrive... (Check celery terminal)")
        sync_pipedrive.apply(
            kwargs={
                "pk": package_template.pk,
                "action": "create",
                "type": "package_template",
                "owner_pk": owner
            }
        )

    if should_sync_stripe:
        logger.info("Creating package template in Stripe... (Check celery terminal)")
        sync_stripe.apply(
            kwargs={
                "pk": package_template.pk,
                "action": "create",
                "type": "package_template",
            }
        )


def update_package_template_sync(
    package_template, should_sync_pipedrive, should_sync_stripe, owner
):
    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = package_template.last_synced_from

    # Check for an ongoing sync
    update_or_create_ongoing_sync(
        type="package_template",
        action="update",
        should_sync_stripe=should_sync_stripe,
        should_sync_pipedrive=should_sync_pipedrive,
        sync_platform=sync_platform,
        owner=owner,
    )

    # Update the package template
    if should_sync_pipedrive:
        logger.info("Updating package template in Pipedrive... (Check celery terminal)")
        sync_pipedrive.delay(package_template.pk, "update", "package_template", owner)
    if should_sync_stripe:
        sync_stripe.delay(package_template.pk, "update", "package_template")


def delete_package_template_sync(
    stripe_id, pipedrive_id, should_sync_pipedrive, should_sync_stripe, owner
):
    # Delete the package template
    if should_sync_pipedrive:
        logger.info("Deleting package template in Pipedrive... (Check celery terminal)")
        sync_pipedrive.delay(pipedrive_id, "delete", "package_template", owner)
    if should_sync_stripe:
        logger.info("Deleting package template in Stripe... (Check celery terminal)")
        sync_stripe.delay(stripe_id, "delete", "package_template")


def create_package_plan_sync(
    package_plan, should_sync_pipedrive, should_sync_stripe, owner
):
    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = package_plan.last_synced_from

    # Check for an ongoing sync
    update_or_create_ongoing_sync(
        type="package_plan",
        action="create",
        should_sync_stripe=should_sync_stripe,
        should_sync_pipedrive=should_sync_pipedrive,
        sync_platform=sync_platform,
        owner=owner,
    )

    # Create the package planc
    if should_sync_pipedrive:
        logger.info("Creating package plan in Pipedrive... (Check celery terminal)")
        sync_pipedrive.apply(
            kwargs={
                "pk": package_plan.pk, 
                "action": "create", 
                "type": "package_plan", 
                "owner_pk": owner
            }
        )


def update_package_plan_sync(
    package_plan, should_sync_pipedrive, should_sync_stripe, owner
):
    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = package_plan.last_synced_from

    # Check for an ongoing sync
    update_or_create_ongoing_sync(
        type="package_plan",
        action="update",
        should_sync_stripe=should_sync_stripe,
        should_sync_pipedrive=should_sync_pipedrive,
        sync_platform=sync_platform,
        owner=owner,
    )

    # Update the package plan
    if should_sync_pipedrive:
        logger.info("Updating package plan in Pipedrive... (Check celery terminal)")
        sync_pipedrive.delay(package_plan.pk, "update", "package_plan", owner)


def delete_package_plan_sync(
    pipedrive_id,
    stripe_subscription_id,
    should_sync_pipedrive,
    should_sync_stripe,
    owner,
):
    # Delete the package plan
    if should_sync_pipedrive:
        logger.info("Deleting package plan in Pipedrive... (Check celery terminal)")
        sync_pipedrive.delay(pipedrive_id, "delete", "package_plan", owner)
    logger.info(f"should_sync_stripe value: {should_sync_stripe}")
    if should_sync_stripe:
        # TODO - Check the package plan type and send the correct type to the sync_stripe task
        logger.info("Deleting subscription in Stripe... (Check celery terminal)")
        sync_stripe.delay(stripe_subscription_id, "delete", "subscription")


def create_service_package_sync(
    package, should_sync_pipedrive, should_sync_stripe, owner
):
    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = package.last_synced_from

    # Check for an ongoing sync
    # update_or_create_ongoing_sync(
    # type='service_package',
    # action='create',
    # should_sync_stripe=should_sync_stripe,
    # should_sync_pipedrive=should_sync_pipedrive,
    # sync_platform=sync_platform
    # )

    # # Create the service package
    if should_sync_pipedrive:
        logger.info("Creating service package in Pipedrive... (Check celery terminal)")
        sync_pipedrive.apply(
            kwargs={"pk": package.pk, "action": "create", "type": "service_package", "owner_pk": owner}
        )
    if should_sync_stripe:
        subscription_id = package.package_plan.stripe_subscription_id
        subscription_pk = StripeSubscription.objects.filter(
            stripe_subscription_id=subscription_id
        ).first().pk
        logger.info("Creating service package in Stripe... (Check celery terminal)")
        print('subscription_pk: ', subscription_pk)
        sync_stripe.apply(
            kwargs={"pk": subscription_pk, "action": "update", "type": "subscription"}
        )


def update_service_package_sync(
    package, should_sync_pipedrive, should_sync_stripe, owner
):
    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = package.last_synced_from

    # Check for an ongoing sync
    # update_or_create_ongoing_sync(
    # type='service_package',
    # action='update',
    # should_sync_stripe=should_sync_stripe,
    # should_sync_pipedrive=should_sync_pipedrive,
    # sync_platform=sync_platform)

    # Update the service Creating service package in Pipedrive...
    if should_sync_pipedrive:
        logger.info("Updating service package in Pipedrive... (Check celery terminal)")
        sync_pipedrive.delay(package.pk, "update", "service_package", owner)
    if should_sync_stripe:
        logger.info("Updating service package in Stripe... (Check celery terminal)")
        sync_stripe.delay(package.pk, "update", "subscription")


def delete_service_package_sync(
    pipedrive_id, stripe_id, should_sync_pipedrive, should_sync_stripe, owner, attachment_id=None
):
    # Delete the service package
    # logger.info("Deleting service package - delete_service_package_sync util ")
    if should_sync_stripe:
        logger.info("Deleting service package in Stripe... (Check celery terminal)")
        subscription_pk = StripeSubscription.objects.filter(
            stripe_subscription_id=stripe_id
        ).first().pk
        sync_stripe.delay(subscription_pk, "update", "subscription")
    if should_sync_pipedrive:
        logger.info("Deleting service package in Pipedrive... (Check celery terminal)")
        sync_pipedrive.delay(pipedrive_id, "delete", "service_package", owner, attachment_id=attachment_id)


# TODO - Create a new package for a customer.
# Accepts a dictionary of customer selected options.
# Returns a ServicePackage object or False.
def create_service_packages(
    customer, package_details, should_sync_pipedrive, should_sync_stripe, subscription_id, owner
):
    try:
        package_plan, _ = PackagePlan.objects.get_or_create(
            stripe_subscription_id=subscription_id,
            defaults={
                "owner": owner,
                "customer": customer,
                "billing_cycle": package_details["billing_cycle"],
                "status": package_details["status"],
                "name": f"{customer.first_name} {customer.last_name} Deal",
                "description": package_details["description"],
                "stripe_subscription_id": package_details.get("stripe_subscription_id", None),
            }
        )
        
        stripe_subscription = StripeSubscription(
            owner=owner,
            stripe_subscription_id=subscription_id,
            package_plan=package_plan,
            customer=customer
        )
        stripe_subscription.save(should_sync_stripe=False)

        # Create a new Service Package
        for package in package_details["packages"]:
            package_template = ServicePackageTemplate.objects.filter(
                name=package["name"]
            ).first()
            service_package = ServicePackage(
                customer=customer,
                package_template=package_template,
                package_plan=package_plan,
                related_app=package["related_app"],
                type=package["type"],
                cost=package_template.cost,
                is_active=not package["requires_onboarding"],
                last_completed=None,
                date_started=None,
                next_scheduled=None,
                action=package_template.action,
                requires_onboarding=package_template.requires_onboarding,
                stripe_subscription_item_id=package.get("stripe_subscription_item_id", None),
                stripe_subscription_item_price_id=package.get("stripe_price_id", None),
            )
            service_package.save(
                should_sync_pipedrive=should_sync_pipedrive,
                should_sync_stripe=should_sync_stripe,
            )
        return package_plan
    except Exception as e:
        logger.error("\nError with create_service_package: ", e)
        return True


# TODO - Update a package for a customer.
# Accepts a dictionary of customer selected options.
# Returns a ServicePackage object or False.
def update_service_package(package):
    logger.info("Updating an Existing ServicePackage...")
    return True
