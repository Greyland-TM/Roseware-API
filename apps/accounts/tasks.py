from roseware.celery import app
from .models import OngoingSync
from datetime import datetime, timedelta
import pytz

@app.task
def delete_old_sync_objects():
    """
        OngoingSync objects should be consumed durring the sync process. If they are not consumed,
        they will be stuck, so just incase, we will delete any that are older than 30 seconds.
    """
    try:
        # Find and delete sync objects that are older than 30 seconds
        sync_array = OngoingSync.objects.all()
        for sync in sync_array:
            if sync.created_at < datetime.now(pytz.utc) - timedelta(seconds=30):
                sync.delete()

    except Exception as error:
        print(f'Error: {error}')
    return True
