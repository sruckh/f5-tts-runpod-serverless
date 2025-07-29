import boto3
import os
from botocore.exceptions import ClientError, NoCredentialsError

# S3 configuration from environment variables
S3_BUCKET = os.environ.get("S3_BUCKET")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Initialize S3 client with error handling
try:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    print(f"✅ S3 client initialized for bucket: {S3_BUCKET}")
except Exception as e:
    print(f"❌ Failed to initialize S3 client: {e}")
    s3_client = None

def upload_to_s3(file_path, object_name):
    """Upload file to S3 with optimized error handling."""
    if not s3_client or not S3_BUCKET:
        print("❌ S3 not configured properly")
        return None
        
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return None
    
    try:
        # Get file size for logging
        file_size = os.path.getsize(file_path)
        print(f"☁️ Uploading {file_size} bytes to s3://{S3_BUCKET}/{object_name}")
        
        s3_client.upload_file(
            file_path, 
            S3_BUCKET, 
            object_name,
            ExtraArgs={'ContentType': 'audio/wav'}  # Set content type for audio files
        )
        
        url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{object_name}"
        print(f"✅ Upload successful: {url}")
        return url
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ S3 upload failed ({error_code}): {e}")
        return None
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def download_from_s3(object_name, file_path):
    """Download file from S3 with optimized error handling."""
    if not s3_client or not S3_BUCKET:
        print("❌ S3 not configured properly")
        return None
    
    try:
        print(f"📥 Downloading s3://{S3_BUCKET}/{object_name} to {file_path}")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        s3_client.download_file(S3_BUCKET, object_name, file_path)
        
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"✅ Download successful: {file_size} bytes")
            return file_path
        else:
            print("❌ Download failed: file not created")
            return None
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            print(f"❌ File not found in S3: {object_name}")
        else:
            print(f"❌ S3 download failed ({error_code}): {e}")
        return None
    except Exception as e:
        print(f"❌ Download error: {e}")
        return None
