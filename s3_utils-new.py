#!/usr/bin/env python3
"""
S3 Utilities for F5-TTS RunPod Serverless - Optimized for Serverless Pattern
============================================================================

Simplified S3 utilities focused on:
- Fast file uploads (output audio)
- Quick voice file downloads
- No model caching (models pre-loaded in container)
- Minimal dependencies and fast initialization
"""

import boto3
import os
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional

# =============================================================================
# S3 CONFIGURATION
# =============================================================================

# S3 configuration from environment variables
S3_BUCKET = os.environ.get("S3_BUCKET")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")  # For S3-compatible services

# =============================================================================
# S3 CLIENT INITIALIZATION
# =============================================================================

# Initialize S3 client with optimized configuration for serverless
s3_client = None

def initialize_s3_client():
    """Initialize S3 client with error handling."""
    global s3_client
    
    if s3_client is not None:
        return s3_client
    
    try:
        if not all([S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
            print("⚠️ S3 credentials not configured - uploads will fail")
            return None
        
        client_config = {
            "service_name": "s3",
            "aws_access_key_id": AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
            "region_name": AWS_REGION,
        }
        
        # Add endpoint URL for S3-compatible services (Backblaze B2, etc.)
        if AWS_ENDPOINT_URL:
            client_config["endpoint_url"] = AWS_ENDPOINT_URL
            print(f"🔗 Using S3-compatible endpoint: {AWS_ENDPOINT_URL}")
        
        s3_client = boto3.client(**client_config)
        print(f"✅ S3 client ready for bucket: {S3_BUCKET}")
        return s3_client
        
    except Exception as e:
        print(f"❌ Failed to initialize S3 client: {e}")
        return None

# Initialize client when module loads
s3_client = initialize_s3_client()

# =============================================================================
# CORE S3 OPERATIONS - Optimized for Serverless
# =============================================================================

def upload_to_s3(local_file_path: str, s3_key: str, make_public: bool = True) -> Optional[str]:
    """
    Upload file to S3 and return public URL.
    Optimized for fast serverless execution.
    
    Args:
        local_file_path: Path to local file to upload
        s3_key: S3 object key (path in bucket)
        make_public: Whether to make file publicly accessible
    
    Returns:
        Public URL if successful, None if failed
    """
    if not s3_client or not S3_BUCKET:
        print("❌ S3 not configured - cannot upload")
        return None
    
    if not os.path.exists(local_file_path):
        print(f"❌ Local file not found: {local_file_path}")
        return None
    
    try:
        file_size = os.path.getsize(local_file_path)
        print(f"☁️ Uploading {file_size} bytes to s3://{S3_BUCKET}/{s3_key}")
        
        # Upload with optimized configuration
        extra_args = {}
        if make_public:
            extra_args['ACL'] = 'public-read'
        
        # Set content type based on file extension
        if s3_key.endswith('.wav'):
            extra_args['ContentType'] = 'audio/wav'
        elif s3_key.endswith('.mp3'):
            extra_args['ContentType'] = 'audio/mpeg'
        
        s3_client.upload_file(local_file_path, S3_BUCKET, s3_key, ExtraArgs=extra_args)
        
        # Generate public URL
        if AWS_ENDPOINT_URL:
            # Custom endpoint URL construction
            public_url = f"{AWS_ENDPOINT_URL}/{S3_BUCKET}/{s3_key}"
        else:
            # Standard AWS S3 URL
            public_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        
        print(f"✅ Upload successful: {public_url}")
        return public_url
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ S3 upload failed ({error_code}): {e}")
        return None
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def download_from_s3(s3_key: str, local_file_path: str) -> bool:
    """
    Download file from S3 to local path.
    Optimized for fast serverless execution.
    
    Args:
        s3_key: S3 object key to download
        local_file_path: Local path to save file
    
    Returns:
        True if successful, False if failed
    """
    if not s3_client or not S3_BUCKET:
        print("❌ S3 not configured - cannot download")
        return False
    
    try:
        print(f"📥 Downloading s3://{S3_BUCKET}/{s3_key} to {local_file_path}")
        
        # Create parent directory if needed
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        
        # Download file
        s3_client.download_file(S3_BUCKET, s3_key, local_file_path)
        
        # Verify download
        if os.path.exists(local_file_path) and os.path.getsize(local_file_path) > 0:
            file_size = os.path.getsize(local_file_path)
            print(f"✅ Download successful: {file_size} bytes")
            return True
        else:
            print("❌ Downloaded file is empty or missing")
            return False
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            print(f"❌ File not found in S3: {s3_key}")
        else:
            print(f"❌ S3 download failed ({error_code}): {e}")
        return False
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False

def check_s3_object_exists(s3_key: str) -> bool:
    """
    Check if an object exists in S3.
    Fast existence check for serverless use.
    
    Args:
        s3_key: S3 object key to check
    
    Returns:
        True if object exists, False otherwise
    """
    if not s3_client or not S3_BUCKET:
        return False
    
    try:
        s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            print(f"❌ Error checking S3 object: {e}")
            return False
    except Exception as e:
        print(f"❌ Error checking S3 object: {e}")
        return False

def list_s3_objects(prefix: str, max_keys: int = 1000) -> list:
    """
    List objects in S3 with given prefix.
    Optimized for serverless with key limits.
    
    Args:
        prefix: S3 key prefix to filter by
        max_keys: Maximum number of keys to return
    
    Returns:
        List of object info dictionaries
    """
    if not s3_client or not S3_BUCKET:
        return []
    
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET, 
            Prefix=prefix, 
            MaxKeys=max_keys
        )
        
        objects = []
        if 'Contents' in response:
            for obj in response['Contents']:
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })
        
        print(f"📋 Listed {len(objects)} objects with prefix: {prefix}")
        return objects
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ S3 list failed ({error_code}): {e}")
        return []
    except Exception as e:
        print(f"❌ List error: {e}")
        return []

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_s3_status() -> dict:
    """
    Get S3 configuration status for debugging.
    Returns configuration and connectivity information.
    """
    status = {
        "configured": bool(s3_client and S3_BUCKET),
        "bucket": S3_BUCKET,
        "region": AWS_REGION,
        "endpoint": AWS_ENDPOINT_URL,
        "credentials": bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
    }
    
    # Test connectivity if configured
    if status["configured"]:
        try:
            s3_client.head_bucket(Bucket=S3_BUCKET)
            status["connectivity"] = True
        except Exception as e:
            status["connectivity"] = False
            status["error"] = str(e)
    else:
        status["connectivity"] = False
    
    return status

def cleanup_temp_files(file_paths: list):
    """
    Clean up temporary files safely.
    Helper function for serverless cleanup.
    
    Args:
        file_paths: List of file paths to delete
    """
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
                print(f"🗑️ Cleaned up: {file_path}")
        except Exception as e:
            print(f"⚠️ Failed to cleanup {file_path}: {e}")

# =============================================================================
# MODULE INITIALIZATION
# =============================================================================

if __name__ == "__main__":
    # Test S3 configuration when run directly
    print("🧪 Testing S3 configuration...")
    status = get_s3_status()
    
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    if status["configured"] and status["connectivity"]:
        print("✅ S3 ready for serverless operations")
    else:
        print("❌ S3 configuration issues detected")