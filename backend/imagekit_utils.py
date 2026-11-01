"""
ImageKit upload utility.
Used by product/category views to upload images when USE_IMAGEKIT=True.
"""
from django.conf import settings


def upload_to_imagekit(file, folder="uploads", file_name=None):
    """
    Upload a file object to ImageKit and return the public URL.
    Returns None if ImageKit is not configured.

    Usage in a view:
        url = upload_to_imagekit(request.FILES['image'], folder='products')
    """
    if not getattr(settings, 'USE_IMAGEKIT', False):
        return None

    try:
        from imagekitio import ImageKit
        from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

        ik = ImageKit(
            private_key=settings.IMAGEKIT_PRIVATE_KEY,
            public_key=settings.IMAGEKIT_PUBLIC_KEY,
            url_endpoint=settings.IMAGEKIT_URL_ENDPOINT,
        )

        options = UploadFileRequestOptions(
            folder=f"/{folder}/",
            is_private_file=False,
        )

        upload = ik.upload_file(
            file=file,
            file_name=file_name or getattr(file, 'name', 'upload'),
            options=options,
        )

        return upload.response_metadata.raw.get('url') or upload.url

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"ImageKit upload failed: {e}")
        return None
