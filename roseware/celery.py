import os, datetime, logging
from django.core import management
from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging



# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "roseware.settings.base")
app = Celery("roseware")
app.config_from_object("django.conf:settings", namespace="CELERY") 

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# # Celery hijacks the root logger and configures it itself by default. 
# # This prevents Celery from doing that. 
# @setup_logging.connect
# def celery_setup_logging(*args, **kwargs):
#     pass

# Schedule tasks
app.conf.beat_schedule = {
    "generate-monthly-marketing-schedules": {
        "task": "apps.marketing_manager.tasks.generate_monthly_marketing_schedules",
        "schedule": crontab(hour=10, minute=0, day_of_month="1"),
        "args": (),
    },
    "create-daily-content": {
        "task": "apps.marketing_manager.tasks.create_daily_content",
        "schedule": crontab(hour=17, minute=0),
        "args": (),
    },
    "debug": {
        "task": "roseware.celery.debug",
        "schedule": datetime.timedelta(seconds=5),
        "args": (),
    },
}

## Debug task ###
@app.task
def debug():
    management.call_command("debug_test")

