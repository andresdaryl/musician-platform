import os
import logging
from minio import Minio
from minio.error import S3Error
from datetime import timedelta
import uuid

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "musician-platform")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


class StorageService:
    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        self.bucket_name = MINIO_BUCKET
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
    
    async def upload_file(self, file_data: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
        try:
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}_{filename}"
            
            # Upload file
            from io import BytesIO
            self.client.put_object(
                self.bucket_name,
                unique_filename,
                BytesIO(file_data),
                length=len(file_data),
                content_type=content_type
            )
            
            # Generate URL
            url = f"http://{MINIO_ENDPOINT}/{self.bucket_name}/{unique_filename}"
            logger.info(f"Uploaded file: {url}")
            return url
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    def get_presigned_url(self, object_name: str, expires: timedelta = timedelta(hours=1)) -> str:
        try:
            url = self.client.presigned_get_object(self.bucket_name, object_name, expires=expires)
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise


storage_service = StorageService()
