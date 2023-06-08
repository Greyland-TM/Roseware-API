from roseware.celery import app
from .models import OngoingSync
from datetime import datetime, timedelta
import pytz

# TODO - This task should filter all of the active PackagePlans and check if they are due for a package delivery
# If they are due, they should send the customers PackagePlan to the respective apps package reciever. (example: duda.tasks.receive_package)
@app.task
def delete_old_sync_objects():
    try:
        #  get all 
        sync_array = OngoingSync.objects.all()
        #  Find the ones that are older than 3 seconds
        for sync in sync_array:
            if sync.created_at < datetime.now(pytz.utc) - timedelta(seconds=5):
                print('Deleting old sync object...')
                sync.delete()

    except Exception as e:
        print(f'Error: {e}')
    return True
