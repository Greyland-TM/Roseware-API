from .models import ServicePackage, ServicePackageTemplate, PackagePlan
from apps.pipedrive.tasks import sync_pipedrive
from apps.stripe.tasks import sync_stripe
from apps.accounts.utils import update_or_create_ongoing_sync

# These functions are called from the .save method of the models.
# Calling them like this allows the tasks to be called in the correct order.
def create_package_template_sync(package_template, should_sync_pipedrive, should_sync_stripe):

    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = package_template.last_synced_from

    # Check for an ongoing sync
    update_or_create_ongoing_sync(
        type='package_template',
        action='create',
        should_sync_stripe=should_sync_stripe,
        should_sync_pipedrive=should_sync_pipedrive,
        sync_platform=sync_platform
    )

    # Start the sync tasks
    if should_sync_pipedrive:
        print('Creating package template in Pipedrive... (Check celery terminal)')
        sync_pipedrive.apply(kwargs={
            'pk': package_template.pk,
            'action': 'create',
            'type': 'package_template'
        })
    if should_sync_stripe:
        print('Creating package template in Stripe... (Check celery terminal)')
        sync_stripe.apply(kwargs={
            'pk': package_template.pk,
            'action': 'create',
            'type': 'package_template'
        })

def update_package_template_sync(package_template, should_sync_pipedrive, should_sync_stripe):
    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = package_template.last_synced_from

    # Check for an ongoing sync
    update_or_create_ongoing_sync(
        type='package_template',
        action='update',
        should_sync_stripe=should_sync_stripe,
        should_sync_pipedrive=should_sync_pipedrive,
        sync_platform=sync_platform
    )

    # Update the package template
    if should_sync_pipedrive:
        print('Updating package template in Pipedrive... (Check celery terminal)')
        sync_pipedrive.delay(package_template.pk, 'update', 'package_template')
    if should_sync_stripe:
        sync_stripe.delay(package_template.pk, 'update', 'package_template')

def delete_package_template_sync(stripe_id, pipedrive_id, should_sync_pipedrive, should_sync_stripe):
    # Delete the package template
    if should_sync_pipedrive:
        print('Deleting package template in Pipedrive... (Check celery terminal)')
        sync_pipedrive.delay(pipedrive_id, 'delete', 'package_template')
    if should_sync_stripe:
        print('Deleting package template in Stripe... (Check celery terminal)')
        sync_stripe.delay(stripe_id, 'delete', 'package_template')

def create_package_plan_sync(package_plan, should_sync_pipedrive, should_sync_stripe):
    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = package_plan.last_synced_from

    # Check for an ongoing sync
    update_or_create_ongoing_sync(
        type='package_plan',
        action='create',
        should_sync_stripe=should_sync_stripe,
        should_sync_pipedrive=should_sync_pipedrive,
        sync_platform=sync_platform
    )

    # Create the package plan
    if should_sync_pipedrive:
        print('Creating package plan in Pipedrive... (Check celery terminal)')
        sync_pipedrive.apply(kwargs={
            'pk': package_plan.pk,
            'action': 'create',
            'type': 'package_plan'
        })

def update_package_plan_sync(package_plan, should_sync_pipedrive, should_sync_stripe):
    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = package_plan.last_synced_from

    # Check for an ongoing sync
    update_or_create_ongoing_sync(
        type='package_plan',
        action='update',
        should_sync_stripe=should_sync_stripe,
        should_sync_pipedrive=should_sync_pipedrive,
        sync_platform=sync_platform
    )

    # Update the package plan
    if should_sync_pipedrive:
        print('Updating package plan in Pipedrive... (Check celery terminal)')
        sync_pipedrive.delay(package_plan.pk, 'update', 'package_plan')

def delete_package_plan_sync(pipedrive_id, stripe_subscription_id, should_sync_pipedrive, should_sync_stripe):
    # Delete the package plan
    if should_sync_pipedrive:
        print('Deleting package plan in Pipedrive... (Check celery terminal)')
        sync_pipedrive.delay(pipedrive_id, 'delete', 'package_plan')
    if should_sync_stripe:
        # TODO - Check the package plan type and send the correct type to the sync_stripe task
        print('Deleting subscription in Stripe... (Check celery terminal)')
        sync_stripe.delay(stripe_subscription_id, 'delete', 'subscription')

def create_service_package_sync(package, should_sync_pipedrive, should_sync_stripe):
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
        print('Creating service package in Pipedrive... (Check celery terminal)')
        sync_pipedrive.apply(kwargs={
            'pk': package.pk,
            'action': 'create',
            'type': 'service_package'
        })
    if should_sync_stripe:
        print('Creating service package in Stripe... (Check celery terminal)')
        sync_stripe.apply(kwargs={
            'pk': package.pk,
            'action': 'create',
            'type': 'service_package'
        })

def update_service_package_sync(package, should_sync_pipedrive, should_sync_stripe):
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

    # Update the service package
    if should_sync_pipedrive:
        print('Updating service package in Pipedrive... (Check celery terminal)')
        sync_pipedrive.delay(package.pk, 'update', 'service_package')
    if should_sync_stripe:
        print('Updating service package in Stripe... (Check celery terminal)')
        sync_stripe.delay(package.pk, 'update', 'subscription')

def delete_service_package_sync(pipedrive_id, stripe_id, should_sync_pipedrive, should_sync_stripe):
    # Delete the service package
    print('Deleting service package...')
    if should_sync_pipedrive:
        print('Deleting service package in Pipedrive... (Check celery terminal)')
        sync_pipedrive.delay(pipedrive_id, 'delete', 'package')
    if should_sync_stripe:
        print('Deleting service package in Stripe... (Check celery terminal)')
        sync_stripe.delay(stripe_id, 'update', 'subscription')


# TODO - Create a new package for a customer.
# Accepts a dictionary of customer selected options.
# Returns a ServicePackage object or False.
def create_service_packages(customer, package_details, should_sync_pipedrive, should_sync_stripe):
    try:
        # Get the package template
        print(package_details)
        packages = package_details["packages"]
        for package in packages:
            related_app = package["related_app"].lower()
            type = package["type"].lower()
            package_template, _ = ServicePackageTemplate.objects.get_or_create(
                related_app=related_app,
                type=type,
                defaults={
                    'requires_onboarding': True,
                    'name': package['name'],
                    'cost': package['price'],
                }
            )

        # Create a new Package Plan
        package_plan = PackagePlan.objects.create(
            customer=customer,
            billing_cycle=package_details["billing_cycle"],
            status=package_details["status"],
            name=f'{customer.first_name} {customer.last_name} Deal',
            description=package_details["description"],
            stripe_subscription_id=package_details.get('stripe_subscription_id', None),
        )
        print(package_plan)

        # Create a new Service Package
        for package in packages:
            related_app = package["related_app"].lower()
            type = package["type"].lower()
            package_template = ServicePackageTemplate.objects.get(
                related_app=related_app,
                type=type,
            )
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
                stripe_subscription_item_id=package.get('stripe_product_id', None),
                stripe_subscription_item_price_id=package.get('stripe_price_id', None),
            )

            service_package.save(should_sync_pipedrive=should_sync_pipedrive, should_sync_stripe=should_sync_stripe)
        return package_plan
    except Exception as e:
        print("\nError with create_service_package: ", e)
        return True


# TODO - Update a package for a customer.
# Accepts a dictionary of customer selected options.
# Returns a ServicePackage object or False.
def update_service_package(package):
    print("Updating an Existing ServicePackage...")
    return True