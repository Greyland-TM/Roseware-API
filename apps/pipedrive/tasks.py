from apps.accounts.models import Customer
from apps.package_manager.models import (PackagePlan, ServicePackage,
                                         ServicePackageTemplate)
from roseware.celery import app
from roseware.utils import make_logger

from .utils import (create_pipedrive_customer, create_pipedrive_deal,
                    create_pipedrive_lead, create_pipedrive_package_template,
                    create_pipedrive_service_package,
                    delete_pipedrive_customer, delete_pipedrive_deal,
                    delete_pipedrive_package_template,
                    delete_pipedrive_service_package,
                    update_pipedrive_customer, update_pipedrive_deal,
                    update_pipedrive_package_template,
                    update_pipedrive_service_package)

# set up the logger
logger = make_logger()

@app.task(default_retry_delay=10, max_retries=3)
def sync_pipedrive(pk, action, type):
    # Get customer details

    try:
        if type == 'customer':
            customer_qs = Customer.objects.filter(pk=pk)
            customer = customer_qs.first()

            # *** Create New Pipedrive Lead ***
            if action == 'create':
                was_lead_created = create_pipedrive_customer(customer)
                if not was_lead_created:
                    logger.error('*** Failed to create customer in Pipedrive ***')
                return was_lead_created

            # *** Update Existing Pipedrive Contact ***
            elif action == 'update':
                was_updated = update_pipedrive_customer(customer)
                if not was_updated:
                    logger.error('*** Failed to update customer in Pipedrive ***')
                return was_updated

            # *** Delete Existing Pipedrive Contact ***
            elif action == 'delete':
                was_deleted = delete_pipedrive_customer(pk)  # On delete, the pk is actually the pipedrive_id
                if not was_deleted:
                    logger.error('*** Failed to delete customer in Pipedrive ***')
                return False

        elif type == 'package_template':
            package_template_qs = ServicePackageTemplate.objects.filter(pk=pk)
            package_template = package_template_qs.first()

            # *** Create New Pipedrive Package_template ***
            if action == 'create':
                was_package_template_created = create_pipedrive_package_template(package_template)
                if not was_package_template_created:
                    logger.error('*** Failed to create package_template in Pipedrive ***')
                return was_package_template_created

            # *** Update Existing Pipedrive Package_template ***
            elif action == 'update':
                was_package_template_updated = update_pipedrive_package_template(package_template)
                if not was_package_template_updated:
                    logger.error('*** Failed to update package_template in Pipedrive ***')
                return was_package_template_updated

            # *** Delete Existing Pipedrive Package_template ***
            elif action == 'delete':
                was_deleted = delete_pipedrive_package_template(pk)  # On delete, the pk is actually the pipedrive_id
                if not was_deleted:
                    logger.error('*** Failed to delete package_template in Pipedrive ***')
                return False

        elif type == 'package_plan':
            package_plan = PackagePlan.objects.filter(pk=pk).first()

            # *** Create New Pipedrive Deal ***
            if action == 'create':
                was_deal_created = create_pipedrive_deal(package_plan)
                if not was_deal_created:
                    logger.error('*** Failed to create deal in Pipedrive ***')
                return was_deal_created

            # *** Update Existing Pipedrive Deal ***
            elif action == 'update':
                was_deal_updated = update_pipedrive_deal(package_plan)
                if not was_deal_updated:
                    logger.error('*** Failed to update deal (normal deal) in Pipedrive ***')
                return was_deal_updated

            # *** Delete Existing Pipedrive Deal ***
            elif action == 'delete':
                was_deleted = delete_pipedrive_deal(pk)  # On delete, the pk is actually the pipedrive_id
                if not was_deleted:
                    logger.error('*** Failed to delete deal in Pipedrive ***')
                return was_deleted

        elif type == 'service_package':
            service_package = ServicePackage.objects.filter(pk=pk).first()

            # *** Create New Pipedrive Deal ***
            if action == 'create':
                was_deal_created = create_pipedrive_service_package(service_package)
                if not was_deal_created:
                    logger.error('*** Failed to attach package to Pipedrive deal ***')
                return was_deal_created

            # *** Update Existing Pipedrive Deal ***
            elif action == 'update':
                was_deal_updated = update_pipedrive_service_package(service_package)
                if not was_deal_updated:
                    logger.error('*** Failed to update deal (service_package) in Pipedrive ***')
                return was_deal_updated

            # *** Delete Existing Pipedrive Deal ***
            elif action == 'delete':
                was_deleted = delete_pipedrive_service_package(service_package)

        elif type == 'lead':
            print('\n\nCREATING PIPEDRRIVE LEAD\n\n')
            customer_qs = Customer.objects.filter(pk=pk)
            customer = customer_qs.first()

            # *** Create New Pipedrive Lead ***
            if action == 'create':
                was_lead_created = create_pipedrive_lead(customer)
                if not was_lead_created:
                    logger.error('*** Failed to create lead in Pipedrive ***')
                return was_lead_created
            return False

    except Exception as error:
        logger.error(f'Failed: {error}')
        raise error
