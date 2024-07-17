import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings
from dotenv import load_dotenv

load_dotenv()

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'image_gallery.settings')
app = Celery('image_gallery', broker='redis://localhost:6379')
print(app)
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.conf.enable_utc = False
app.conf.update(timezone='America/New_York')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
# celery -A image_gallery.celery worker --pool=solo -l info << command to initiate celery worker celery -A
# celery -A image_gallery beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler <<
# command to initiate
app.conf.beat_schedule = {
    'delete_from_trash': {
        'task': 'image_gallery_app.tasks.auto_delete_images_and_folder',
        'schedule': crontab(hour=6, minute=1)
    }
}


# Load task modules from all registered Django app configs.
@app.task(bind=True)
def debug_task(self):
    print('celery')
    print(f'Request: {self.request!r}')
