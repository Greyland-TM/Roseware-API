from roseware.celery import app
from apps.integrations.utils import process_integrations_packages
from .models import ServicePackage
from roseware.utils import make_logger

logger = make_logger()

@app.task
def daily_package_check():
    logger.info('Starting daily_package_check')

    try:
        # Get the all of the packages
        package_array = ServicePackage.objects.all()

        # Seperate them by related_app
        integrations_packages = package_array.filter(related_app='integrations')

        # Send the packages to the respective apps for handeling
        process_integrations_packages(integrations_packages)
    except Exception as e:
        logger.error(f'daily_package_check failed Error: {e}')
    return True

@app.task
def sync_pipedrive_and_stripe(pipedrive_fields, stripe_fields):
    from apps.pipedrive.tasks import sync_pipedrive
    from apps.stripe.tasks import sync_stripe

    sync_pipedrive(pipedrive_fields['pk'], pipedrive_fields['action'], pipedrive_fields['type'])
    sync_stripe(stripe_fields['pk'], stripe_fields['action'], stripe_fields['type'])
