import os
from celery import Celery
from celery.schedules import crontab
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "roseware.settings.base")

app = Celery("roseware")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-for-packages': {
        'task': 'apps.accounts.tasks.delete_old_sync_objects',
        'schedule': 30,
        'args': (),
    },
    'generate-monthly-marketing-schedules': {
        'task': 'apps.marketing_manager.tasks.generate_monthly_marketing_schedules',
        'schedule': crontab(hour=10, minute=0, day_of_month='1'),
        'args': (),
    }
}
