import boto3
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError, NoCredentialsError

# S3 configuration from environment variables
S3_BUCKET = os.environ.get("S3_BUCKET")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")  # For S3-compatible services like Backblaze B2

# Initialize S3 client with error handling
try:
    client_config = {
        "service_name": "s3",
        "aws_access_key_id": AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
        "region_name": AWS_REGION,
    }
    
    # Add endpoint URL for S3-compatible services (Backblaze B2, DigitalOcean Spaces, etc.)
    if AWS_ENDPOINT_URL:
        client_config["endpoint_url"] = AWS_ENDPOINT_URL
        print(f"🔗 Using custom S3 endpoint: {AWS_ENDPOINT_URL}")
    
    s3_client = boto3.client(**client_config)
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
        
        # Generate public URL - handle custom endpoints like Backblaze B2
        if AWS_ENDPOINT_URL:
            # For custom endpoints, use the endpoint URL directly
            url = f"{AWS_ENDPOINT_URL.rstrip('/')}/{S3_BUCKET}/{object_name}"
        else:
            # Standard AWS S3 URL format
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

def generate_presigned_download_url(object_name, expiration=3600):
    """
    Generate a presigned URL for secure S3 object download.
    
    Args:
        object_name (str): S3 object key/name
        expiration (int): Time in seconds for URL to remain valid (default: 1 hour)
    
    Returns:
        str: Presigned URL for secure download, or None if failed
    """
    if not s3_client or not S3_BUCKET:
        print("❌ S3 not configured for presigned URL generation")
        return None
    
    try:
        print(f"🔐 Generating presigned URL for s3://{S3_BUCKET}/{object_name} (expires in {expiration}s)")
        
        # Generate presigned URL for GET operation
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': object_name},
            ExpiresIn=expiration
        )
        
        print(f"✅ Presigned URL generated successfully")
        return presigned_url
        
    except ClientError as e:
        print(f"❌ Failed to generate presigned URL: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error generating presigned URL: {e}")
        return None

def upload_to_s3_with_presigned_url(file_path, object_name, expiration=3600):
    """
    Upload file to S3 and return a presigned URL for secure download.
    
    Args:
        file_path (str): Local file path to upload
        object_name (str): S3 object key/name
        expiration (int): Presigned URL expiration in seconds
    
    Returns:
        str: Presigned download URL, or None if upload/URL generation failed
    """
    # First upload the file
    s3_url = upload_to_s3(file_path, object_name)
    if not s3_url:
        return None
    
    # Then generate presigned URL for secure access
    presigned_url = generate_presigned_download_url(object_name, expiration)
    return presigned_url

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

# Model syncing functions removed - models now stored persistently in /runpod-volume
# S3 is used only for voice files (input) and generated audio (output)

def list_s3_objects(prefix=""):
    """List objects in S3 bucket with optional prefix filter."""
    if not s3_client or not S3_BUCKET:
        print("❌ S3 not configured properly")
        return []
    
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if 'Contents' in response:
            return [obj['Key'] for obj in response['Contents']]
        return []
    except Exception as e:
        print(f"❌ Error listing S3 objects: {e}")
        return []

def check_s3_object_exists(object_name):
    """Check if an object exists in S3 bucket."""
    if not s3_client or not S3_BUCKET:
        return False
    
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=object_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return False
        print(f"❌ Error checking S3 object: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking S3 object: {e}")
        return False

def download_file_from_s3_to_memory(object_name):
    """Download a file from S3 and return it as a byte stream."""
    if not s3_client or not S3_BUCKET:
        print("S3 not configured properly")
        return None
    try:
        s3_object = s3_client.get_object(Bucket=S3_BUCKET, Key=object_name)
        return s3_object['Body'].read()
    except ClientError as e:
        if e.response['Error']['Code'] == "404":
            print(f"The object {object_name} does not exist.")
        else:
            print(f"An error occurred: {e}")
        return None
