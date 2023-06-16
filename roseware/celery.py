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

# Celery Beat Schedule
# app.conf.beat_schedule = {
#     # 'check-for-packages': {
#     #     'task': 'apps.package_manager.tasks.daily_package_check',
#     #     'schedule': crontab(minute='*/1'),
#     #     'args': (),
#     # },
#     'debug': {
#         'task': 'apps.package_manager.tasks.debug_task',
#         'schedule': 15.0,
#         'args': ('testing', 'testing2'),
#     },
# }
app.conf.beat_schedule = {
    'check-for-packages': {
        'task': 'apps.accounts.tasks.delete_old_sync_objects',
        'schedule': 3,
        'args': (),
    },
    'create-daily-posts': {
        'task': 'apps.marketing_manager.tasks.create_daily_posts',
        'schedule': 3,
        'args': (),
    }
}
