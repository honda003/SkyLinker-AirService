import os
from django.conf import settings
from celery import Celery
from celery.schedules import crontab
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkyLinker.settings')

app = Celery('SkyLinker')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks([
    'Home', 'About', 'Services', 'Maintenance', 'Operator', 'AMP',
    'AircraftData', 'LDND', 'UpcomingTasks', 'AirlineOperations',
    'ItineraryBuilder', 'Routing', 'FleetAssignment'
])  #lambda:settings.INSTALLED_APPS

app.conf.beat_schedule = {
    'add-every-hour' : {
        'task' : 'send_upcoming_tasks_monthly_email',
        'schedule' : crontab(minute=0)  #crontab(hour=0, minute=0, day_of_month='1') This sets the task to run at 00:00 (midnight) on the first day of each month. Adjust the hour and minute values as needed for your specific scheduling requirements.
    }
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')