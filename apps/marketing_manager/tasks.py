from roseware.celery import app
from apps.package_manager.models import ServicePackage
from .models import DailyContent, CustomerSelectedPlatform
from apps.marketing_manager.utils import create_monthly_marketing_schedule, create_social_post
from datetime import datetime
from pytz import timezone
from roseware.utils import make_logger

logger = make_logger(__name__)

@app.task
def generate_monthly_marketing_schedules():
    try:
        #  Get all package plans that are marketing, and create a monthly marketing schedule for each
        service_packages = ServicePackage.objects.filter(type='Social')
        print(f"Found {len(service_packages)} marketing packages")
        for package in service_packages:
            print('Creating monthly marketing schedule for customer: ', package.customer)
            monthly_marketing_schedule = create_monthly_marketing_schedule(package.customer)

        if monthly_marketing_schedule:
            print("Monthly Marketing Schedule Created")
        else:
            print("Failed to create Monthly Marketing Schedule")

    except Exception as e:
        print(f'Error: {e}')
    return True

@app.task
def create_daily_content():
    print('creating daily content')
    
    pacific = timezone('US/Pacific')
    current_date_pacific = datetime.now(pacific).date()
    
    scheduled_content = DailyContent.objects.filter(scheduled_date=current_date_pacific)
    
    for content in scheduled_content:
        customer = content.weekly_topic.schedule.customer
        platforms = CustomerSelectedPlatform.objects.filter(customer=customer)
        create_social_post(content, platforms)
            
    return True
