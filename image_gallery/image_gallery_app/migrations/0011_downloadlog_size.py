# Generated by Django 5.0.6 on 2024-06-10 06:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('image_gallery_app', '0010_alter_folder_cover_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='downloadlog',
            name='size',
            field=models.FloatField(default=0.0),
        ),
    ]
