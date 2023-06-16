from roseware.celery import app
from apps.accounts.models import Customer
from apps.package_manager.models import PackagePlan
from apps.marketing_manager.utils import create_monthly_marketing_schedule


@app.task
def send_daily_posts():
    try:
        #  Get all package plans that are marketing, and create a monthly marketing schedule for each
        package_plans = PackagePlan.objects.filter(type='marketing')
        for plan in package_plans:
            monthly_marketing_schedule = create_monthly_marketing_schedule(plan.customer)

        if monthly_marketing_schedule:
            print("Monthly Marketing Schedule Created")
        else:
            print("Failed to create Monthly Marketing Schedule")

    except Exception as e:
        print(f'Error: {e}')
    return True
