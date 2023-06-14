from django.core.management.base import BaseCommand

from apps.accounts.models import Customer
from apps.marketing_manager.models import WeeklyTopic
from apps.marketing_manager.utils import (create_customer_monthly_schedule,
                                          create_schedules_daily_content,
                                          create_schedules_weekly_topics)


class Command(BaseCommand):
    """ This command gets a monthly schedule from chat gpt """

    def handle(self, *args, **kwargs):
        """ Main command handler """
        
        # Create the schedule
        customer = Customer.objects.get(pk=61)
        schedule = create_customer_monthly_schedule(customer)
        if not schedule["was_created"]:
            print("Failed to create the schedule. Stop command here")
            return

        # Create the weekly topics
        for attempt in range(3):
            weeks = create_schedules_weekly_topics(schedule['schedule'])
            if weeks['was_created']:
                break
            else:
                print(f"There was an issue generating the topics on attempt {attempt + 1}. Trying again now.")
                WeeklyTopic.objects.filter(schedule=schedule['schedule']).delete()
                
        # Create the daily contents
        for attempt in range(3):
            contents = create_schedules_daily_content(schedule['schedule'])
            if contents['was_created']:
                break
            else:
                print(f"There was an issue generating the topics on attempt {attempt + 1}. Trying again now.")

        print('Done!')
        return
