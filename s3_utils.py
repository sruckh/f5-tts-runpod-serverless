import boto3
import os

S3_BUCKET = os.environ.get("S3_BUCKET")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

def upload_to_s3(file_path, object_name):
    """Upload a file to an S3 bucket."""
    try:
        s3_client.upload_file(file_path, S3_BUCKET, object_name)
        return f"https://{S3_BUCKET}.s3.amazonaws.com/{object_name}"
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        return None

def download_from_s3(object_name, file_path):
    """Download a file from an S3 bucket."""
    try:
        s3_client.download_file(S3_BUCKET, object_name, file_path)
        return file_path
    except Exception as e:
        print(f"Error downloading from S3: {e}")
        return None
