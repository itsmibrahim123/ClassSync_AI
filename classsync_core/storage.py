"""
S3 storage service for file uploads and management.
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
from datetime import datetime
from classsync_api.config import settings
import logging

logger = logging.getLogger(__name__)


class S3Service:
    """Service for interacting with S3 storage."""

    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region
        )
        self.bucket_name = settings.s3_bucket_name

    def generate_s3_key(self, institution_id: int, filename: str, dataset_type: str) -> str:
        """
        Generate S3 key (path) for uploaded file.

        Format: uploads/{institution_id}/{dataset_type}/{timestamp}_{filename}

        Args:
            institution_id: Institution ID for multi-tenancy
            filename: Original filename
            dataset_type: Type of dataset (courses, teachers, rooms, sections)

        Returns:
            S3 key string
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        s3_key = f"uploads/{institution_id}/{dataset_type}/{timestamp}_{filename}"
        return s3_key

    def upload_file(
            self,
            file_content: bytes,
            s3_key: str,
            content_type: str = 'application/octet-stream'
    ) -> bool:
        """
        Upload file to S3.

        Args:
            file_content: File content as bytes
            s3_key: S3 key (path) for the file
            content_type: MIME type of the file

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )
            logger.info(f"Successfully uploaded file to S3: {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            return False

    def download_file(self, s3_key: str) -> Optional[bytes]:
        """
        Download file from S3.

        Args:
            s3_key: S3 key (path) of the file

        Returns:
            File content as bytes, or None if failed
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            content = response['Body'].read()
            logger.info(f"Successfully downloaded file from S3: {s3_key}")
            return content

        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {e}")
            return None

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete file from S3.

        Args:
            s3_key: S3 key (path) of the file

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Successfully deleted file from S3: {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting from S3: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3.

        Args:
            s3_key: S3 key (path) of the file

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError:
            return False

    def get_file_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for file download.

        Args:
            s3_key: S3 key (path) of the file
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL string, or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None


# Global S3 service instance
s3_service = S3Service()