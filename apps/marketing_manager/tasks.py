from roseware.celery import app
from apps.package_manager.models import ServicePackage
from .models import DailyContent, CustomerSelectedPlatform
from apps.marketing_manager.utils import create_monthly_marketing_schedule, create_social_post
from datetime import datetime
from pytz import timezone
import logging

logger = logging.getLogger(__name__)

@app.task
def generate_monthly_marketing_schedules():
    try:
        #  Get all package plans that are marketing, and create a monthly marketing schedule for each
        service_packages = ServicePackage.objects.filter(type='Social')
        logger.info(f"Found {len(service_packages)} marketing packages")
        for package in service_packages:
            logger.info('Creating monthly marketing schedule for customer: ', package.customer)
            monthly_marketing_schedule = create_monthly_marketing_schedule(package.customer)

        if monthly_marketing_schedule:
            logger.info("Monthly Marketing Schedule Created")
        else:
            logger.info("Failed to create Monthly Marketing Schedule")

    except Exception as e:
        logger.error(f'Error: {e}')
    return True

@app.task
def create_daily_content():
    logger.info('creating daily content')
    
    pacific = timezone('US/Pacific')
    current_date_pacific = datetime.now(pacific).date()
    
    scheduled_content = DailyContent.objects.filter(scheduled_date=current_date_pacific)
    
    for content in scheduled_content:
        customer = content.weekly_topic.schedule.customer
        platforms = CustomerSelectedPlatform.objects.filter(customer=customer)
        create_social_post(content, platforms)
            
    return True
