from django.core.management.base import BaseCommand

from apps.accounts.models import Customer
from apps.marketing_manager.models import WeeklyTopic
from apps.marketing_manager.utils import create_monthly_marketing_schedule
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """ This command gets a monthly schedule from chat gpt """

    def handle(self, *args, **kwargs):
        """ Main command handler """
        
        # Create the schedule
        customer = Customer.objects.all().first()
        monthly_marketing_schedule = create_monthly_marketing_schedule(customer)
        
        if monthly_marketing_schedule:
            logger.info("Monthly Marketing Schedule Created")
        else:
            logger.error("Failed to create Monthly Marketing Schedule")
