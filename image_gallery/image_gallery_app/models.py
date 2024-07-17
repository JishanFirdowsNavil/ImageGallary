from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _


# Create your models here.

class CustomUser(AbstractUser):
    first_name = models.CharField(max_length=220, null=True, blank=True)
    last_name = models.CharField(max_length=220, null=True, blank=True)
    email = models.EmailField(_('email'), unique=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    profile_picture = models.ImageField(upload_to=f'media/profile_images/', null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    groups = models.ManyToManyField(Group, blank=True, related_name='custom_users')
    user_permissions = models.ManyToManyField(Permission, blank=True, related_name='custom_users')

    def __str__(self):
        return self.username


class Folder(models.Model):
    folder_uuid = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=220, null=True, blank=True)
    size = models.FloatField(default=0.0)
    event_date = models.DateField(null=True, blank=True)
    created_on = models.DateField(auto_now_add=True)
    cover_photo = models.ImageField(upload_to=f'media/cover_photo/', null=True, blank=True)

    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    added_to_trash = models.BooleanField(default=False)
    added_to_trash_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Round image_size to 2 decimal places
        self.size = round(self.size, 2)
        super(Folder, self).save(*args, **kwargs)


class Image(models.Model):
    image_uuid = models.CharField(max_length=40, unique=True)
    image_name = models.CharField(max_length=220, null=True, blank=True)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True, related_name='folder')
    compact_image = models.ImageField(upload_to=f'media/compact_images/', null=True, blank=True)
    image_size = models.FloatField(default=0.0)
    created_on = models.DateField(auto_now_add=True)
    previous_folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='previous_folder')
    added_to_trash_date = models.DateField(null=True, blank=True)

    s3_link = models.TextField(null=True, blank=True)

    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.image_name

    def save(self, *args, **kwargs):
        # Round image_size to 2 decimal places
        self.image_size = round(self.image_size, 2)
        super(Image, self).save(*args, **kwargs)


class DownloadLog(models.Model):
    download_uuid = models.CharField(max_length=40, unique=True)
    file_name = models.CharField(max_length=220, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    size = models.FloatField(default=0.0)
    downloaded_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.file_name
