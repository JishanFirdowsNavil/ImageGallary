from celery import shared_task
from .models import *
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from .delete_object_s3 import delete_objects


@shared_task(bind=True)
def auto_delete_images_and_folder(self):
    print('daily delete task')
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    folders = Folder.objects.filter(added_to_trash_date__lte=thirty_days_ago, added_to_trash=True)
    for folder in folders:
        images = Image.objects.filter(Q(folder=folder) | Q(previous_folder=folder))
        keys = [image.s3_link for image in images]
        if keys:
            deleted = delete_objects(keys)
            if not deleted:
                return False
        images.delete()
        folder.delete()
    trash_folder = Folder.objects.get_or_create(name='Trash')[0]
    trash_images = Image.objects.filter(added_to_trash_date__lte=thirty_days_ago, folder=trash_folder)
    keys = [image.s3_link for image in trash_images]

    deleted = delete_objects(keys)
    if not deleted:
        return False
    trash_images.delete()
    return True
