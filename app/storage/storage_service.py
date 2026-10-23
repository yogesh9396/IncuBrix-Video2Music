import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Union
from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        self.local_base_dir = Path(settings.STORAGE_LOCAL_DIR).resolve()
        self.local_base_dir.mkdir(parents=True, exist_ok=True)
        self.s3_client = None

        if self.storage_type == "s3":
            try:
                import boto3
                self.s3_client = boto3.client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL,
                    aws_access_key_id=settings.S3_ACCESS_KEY,
                    aws_secret_access_key=settings.S3_SECRET_KEY,
                    region_name=settings.S3_REGION,
                )
                # Ensure bucket exists
                try:
                    self.s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
                except Exception:
                    try:
                        self.s3_client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
                        logger.info(f"Created S3 bucket {settings.S3_BUCKET_NAME}")
                    except Exception as bex:
                        logger.warning(f"Could not create S3 bucket {settings.S3_BUCKET_NAME}: {bex}")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}. Falling back to local storage.")
                self.storage_type = "local"

    def get_job_dir(self, job_id: str) -> Path:
        job_dir = self.local_base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def get_file_path(self, job_id: str, relative_path: str) -> Path:
        return self.get_job_dir(job_id) / relative_path

    def save_file(self, job_id: str, relative_path: str, source: Union[bytes, str, Path]) -> str:
        """
        Saves a file into storage (local directory and optionally uploads to S3).
        Returns the download URL or relative path identifier.
        """
        dest_path = self.get_file_path(job_id, relative_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(source, bytes):
            dest_path.write_bytes(source)
        elif isinstance(source, (str, Path)):
            src_path = Path(source)
            if src_path.resolve() != dest_path.resolve():
                shutil.copy2(src_path, dest_path)

        if self.storage_type == "s3" and self.s3_client:
            s3_key = f"{job_id}/{relative_path.replace(os.sep, '/')}"
            try:
                self.s3_client.upload_file(str(dest_path), settings.S3_BUCKET_NAME, s3_key)
                logger.info(f"Uploaded {relative_path} to s3://{settings.S3_BUCKET_NAME}/{s3_key}")
            except Exception as e:
                logger.error(f"S3 upload failed for {s3_key}: {e}")

        # Always return local artifact download path
        return f"{settings.API_PREFIX}/artifacts/{job_id}/{relative_path.replace(os.sep, '/')}"

    def file_exists(self, job_id: str, relative_path: str) -> bool:
        return self.get_file_path(job_id, relative_path).exists()


storage_service = StorageService()
