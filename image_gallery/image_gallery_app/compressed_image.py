from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.base import ContentFile

from PIL import Image, ImageOps
import tempfile
import shutil


def compressed_image(image_data, original_file_name, height, width):
    """
    Compress an image using Pillow.
    Parameters:
    - image_data: BytesIO object containing the image data.
    - quality: The quality of the compressed image (0-100). Higher values mean better quality.
    Returns:
    - InMemoryUploadedFile: Compressed image data.
    """
    image = Image.open(image_data)
    resized_image = image.resize((height, width))

    image_bytes_io = BytesIO()
    resized_image.save(image_bytes_io, format='PNG')
    image_bytes = image_bytes_io.getvalue()

    # Create and return the InMemoryUploadedFile
    return InMemoryUploadedFile(
        ContentFile(image_bytes),
        field_name='image',  # Replace with the name of your model's ImageField
        name=original_file_name,
        content_type='image/png',
        size=len(image_bytes),
        charset=None
    )
