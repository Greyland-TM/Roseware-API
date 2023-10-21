from roseware.celery import app
from apps.accounts.models import OngoingSync
import  logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@app.task(default_retry_delay=10, max_retries=3, autoretry_for=(Exception, ))
def ongoing_sync_failsafe_check():
    print("Running ongoing_sync_failsafe_check")

    # Delete ongoing syncs that are older than 5 minutes
    active_syncs = OngoingSync.objects.filter(created_at__gte=datetime.now()-timedelta(seconds=30))
    for sync in active_syncs:
        sync.delete()

    return True