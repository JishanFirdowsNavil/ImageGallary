from django.apps import AppConfig


class ImageGalleryAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'image_gallery_app'

    def ready(self) -> None:
        import image_gallery_app.signals
