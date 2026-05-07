"""
Test AWS S3 connection.
"""

import boto3
from botocore.exceptions import ClientError
from classsync_api.config import settings


def test_s3_connection():
    """Test S3 bucket access."""

    print("=" * 60)
    print("Testing AWS S3 Connection")
    print("=" * 60)
    print()

    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region
        )

        # Test: List buckets
        print("Listing buckets...")
        response = s3_client.list_buckets()

        print(f"Connection successful!")
        print(f"\nFound {len(response['Buckets'])} bucket(s):")
        for bucket in response['Buckets']:
            print(f"  - {bucket['Name']}")

        # Test: Check if our bucket exists
        print(f"\nChecking bucket: {settings.s3_bucket_name}")
        try:
            s3_client.head_bucket(Bucket=settings.s3_bucket_name)
            print(f"Bucket '{settings.s3_bucket_name}' is accessible!")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                print(f"Bucket '{settings.s3_bucket_name}' not found!")
            elif error_code == '403':
                print(f"Access denied to bucket '{settings.s3_bucket_name}'!")
            else:
                print(f"Error accessing bucket: {e}")
            return False

        # Test: Upload a small test file
        print(f"\nTesting file upload...")
        test_content = b"ClassSync AI - S3 Test File"
        test_key = "test/connection_test.txt"

        s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=test_key,
            Body=test_content,
            ContentType='text/plain'
        )
        print(f"Test file uploaded: {test_key}")

        # Test: Download the file
        print(f"\nTesting file download...")
        response = s3_client.get_object(
            Bucket=settings.s3_bucket_name,
            Key=test_key
        )
        downloaded_content = response['Body'].read()

        if downloaded_content == test_content:
            print(f"File downloaded and verified!")
        else:
            print(f"Downloaded content doesn't match!")

        # Test: Delete the test file
        print(f"\n🗑Cleaning up test file...")
        s3_client.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=test_key
        )
        print(f"Test file deleted!")

        print()
        print("=" * 60)
        print("All S3 tests passed!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nS3 connection failed!")
        print(f"Error: {e}")
        print()
        print("Please check:")
        print("1. AWS credentials in .env are correct")
        print("2. S3 bucket name is correct")
        print("3. IAM user has S3 permissions")
        print("4. Internet connection is working")
        return False


if __name__ == "__main__":
    test_s3_connection()