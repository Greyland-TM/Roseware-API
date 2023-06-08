web: gunicorn roseware.wsgi --bind 0.0.0.0:$PORT --log-file -
worker: celery -A roseware worker --concurrency 4 -l info --logfile roseware_worker.log
beat: celery -A roseware beat -l info --logfile roseware_beat.log --pidfile /tmp/celerybeat.pid