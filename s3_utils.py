#!/usr/bin/env python3
"""
S3 Client for F5-TTS RunPod Serverless

Handles S3 operations for audio file input/output with proper error handling
and retry logic. Integrates with RunPod's S3 utilities.
"""

import os
import sys
import boto3
import logging
import time
from pathlib import Path
from typing import Optional, Union
from botocore.exceptions import ClientError, NoCredentialsError

# Add container app directory to path
sys.path.append('/app')

try:
    from setup_network_venv import (  # config.py
        S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
        AWS_REGION, AWS_ENDPOINT_URL, S3_RETRY_COUNT, S3_RETRY_DELAY,
        TEMP_PATH
    )
except ImportError:
    # Fallback to environment variables if config not available
    S3_BUCKET = os.getenv("S3_BUCKET")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID") 
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")
    S3_RETRY_COUNT = 3
    S3_RETRY_DELAY = 2
    TEMP_PATH = Path("/tmp")

# Setup logging
logger = logging.getLogger(__name__)

class S3Client:
    """S3 client with error handling and retry logic."""
    
    def __init__(self):
        """Initialize S3 client with credentials."""
        self.bucket = S3_BUCKET
        self.session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        
        # Create S3 client
        s3_config = {}
        if AWS_ENDPOINT_URL:
            s3_config['endpoint_url'] = AWS_ENDPOINT_URL
            
        self.s3 = self.session.client('s3', **s3_config)
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate S3 configuration."""
        if not self.bucket:
            raise ValueError("S3_BUCKET environment variable is required")
        if not AWS_ACCESS_KEY_ID:
            raise ValueError("AWS_ACCESS_KEY_ID environment variable is required")
        if not AWS_SECRET_ACCESS_KEY:
            raise ValueError("AWS_SECRET_ACCESS_KEY environment variable is required")
    
    def _retry_operation(self, operation, *args, **kwargs):
        """Retry S3 operations with exponential backoff."""
        last_exception = None
        
        for attempt in range(S3_RETRY_COUNT):
            try:
                return operation(*args, **kwargs)
            except ClientError as e:
                last_exception = e
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                logger.warning(f"S3 operation failed (attempt {attempt + 1}/{S3_RETRY_COUNT}): {error_code}")
                
                if attempt < S3_RETRY_COUNT - 1:
                    delay = S3_RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error in S3 operation: {e}")
                break
        
        raise last_exception
    
    def upload_file(self, local_path: Union[str, Path], s3_key: str) -> str:
        """
        Upload file to S3 and return the URL.
        
        Args:
            local_path: Path to local file
            s3_key: S3 key (path) for the uploaded file
            
        Returns:
            S3 URL of uploaded file
        """
        try:
            local_path = Path(local_path)
            
            if not local_path.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")
            
            logger.info(f"Uploading {local_path} to s3://{self.bucket}/{s3_key}")
            
            # Upload with retry
            self._retry_operation(
                self.s3.upload_file,
                str(local_path),
                self.bucket,
                s3_key
            )
            
            # Generate URL
            if AWS_ENDPOINT_URL:
                url = f"{AWS_ENDPOINT_URL}/{self.bucket}/{s3_key}"
            else:
                url = f"https://s3.{AWS_REGION}.amazonaws.com/{self.bucket}/{s3_key}"
            
            logger.info(f"Successfully uploaded to: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            raise
    
    def download_file(self, s3_key: str, local_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Download file from S3.
        
        Args:
            s3_key: S3 key of file to download
            local_path: Local path to save file (optional)
            
        Returns:
            Path to downloaded file
        """
        try:
            if local_path is None:
                # Generate temporary filename
                filename = Path(s3_key).name
                local_path = TEMP_PATH / filename
            
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading s3://{self.bucket}/{s3_key} to {local_path}")
            
            # Download with retry
            self._retry_operation(
                self.s3.download_file,
                self.bucket,
                s3_key,
                str(local_path)
            )
            
            if not local_path.exists():
                raise RuntimeError(f"Download failed - file not created: {local_path}")
            
            logger.info(f"Successfully downloaded to: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download {s3_key}: {e}")
            raise
    
    def download_from_url(self, s3_url: str, local_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Download file from S3 URL.
        
        Args:
            s3_url: Full S3 URL (s3://bucket/key or https://...)
            local_path: Local path to save file (optional)
            
        Returns:
            Path to downloaded file
        """
        try:
            # Parse S3 URL to extract bucket and key
            if s3_url.startswith('s3://'):
                # s3://bucket/key format
                s3_parts = s3_url[5:].split('/', 1)
                if len(s3_parts) != 2:
                    raise ValueError(f"Invalid S3 URL format: {s3_url}")
                bucket, s3_key = s3_parts
                
                if bucket != self.bucket:
                    logger.warning(f"URL bucket ({bucket}) differs from configured bucket ({self.bucket})")
            
            elif 'amazonaws.com' in s3_url or AWS_ENDPOINT_URL in s3_url:
                # HTTP(S) URL format
                # Extract key from URL
                if f"/{self.bucket}/" in s3_url:
                    s3_key = s3_url.split(f"/{self.bucket}/", 1)[1]
                else:
                    raise ValueError(f"Cannot extract S3 key from URL: {s3_url}")
            
            else:
                raise ValueError(f"Unsupported URL format: {s3_url}")
            
            return self.download_file(s3_key, local_path)
            
        except Exception as e:
            logger.error(f"Failed to download from URL {s3_url}: {e}")
            raise
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for S3 object.
        
        Args:
            s3_key: S3 key of the object
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        try:
            url = self._retry_operation(
                self.s3.generate_presigned_url,
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for {s3_key}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise

# Global S3 client instance
_s3_client = None

def get_s3_client() -> S3Client:
    """Get global S3 client instance."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client

# Convenience functions
def upload_audio_to_s3(local_path: Union[str, Path], prefix: str = "audio") -> str:
    """Upload audio file to S3 with timestamp prefix."""
    local_path = Path(local_path)
    timestamp = int(time.time())
    s3_key = f"{prefix}/{timestamp}_{local_path.name}"
    
    client = get_s3_client()
    return client.upload_file(local_path, s3_key)

def download_audio_from_s3(s3_url: str) -> Path:
    """Download audio file from S3 URL."""
    client = get_s3_client()
    return client.download_from_url(s3_url)

def upload_subtitles_to_s3(local_path: Union[str, Path]) -> str:
    """Upload subtitle file to S3."""
    return upload_audio_to_s3(local_path, "subtitles")

# Test function
if __name__ == "__main__":
    """Test S3 client functionality."""
    try:
        client = get_s3_client()
        logger.info("S3 client initialized successfully")
        
        # Test basic configuration
        logger.info(f"Bucket: {client.bucket}")
        logger.info(f"Region: {AWS_REGION}")
        
    except Exception as e:
        logger.error(f"S3 client test failed: {e}")
        sys.exit(1)#!/usr/bin/env python3
"""
S3 Client for F5-TTS RunPod Serverless

Handles S3 operations for audio file input/output with proper error handling
and retry logic. Integrates with RunPod's S3 utilities.
"""

import os
import sys
import boto3
import logging
import time
from pathlib import Path
from typing import Optional, Union
from botocore.exceptions import ClientError, NoCredentialsError

# Add container app directory to path
sys.path.append('/app')

try:
    from setup_network_venv import (  # config.py
        S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
        AWS_REGION, AWS_ENDPOINT_URL, S3_RETRY_COUNT, S3_RETRY_DELAY,
        TEMP_PATH
    )
except ImportError:
    # Fallback to environment variables if config not available
    S3_BUCKET = os.getenv("S3_BUCKET")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID") 
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")
    S3_RETRY_COUNT = 3
    S3_RETRY_DELAY = 2
    TEMP_PATH = Path("/tmp")

# Setup logging
logger = logging.getLogger(__name__)

class S3Client:
    """S3 client with error handling and retry logic."""
    
    def __init__(self):
        """Initialize S3 client with credentials."""
        self.bucket = S3_BUCKET
        self.session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        
        # Create S3 client
        s3_config = {}
        if AWS_ENDPOINT_URL:
            s3_config['endpoint_url'] = AWS_ENDPOINT_URL
            
        self.s3 = self.session.client('s3', **s3_config)
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate S3 configuration."""
        if not self.bucket:
            raise ValueError("S3_BUCKET environment variable is required")
        if not AWS_ACCESS_KEY_ID:
            raise ValueError("AWS_ACCESS_KEY_ID environment variable is required")
        if not AWS_SECRET_ACCESS_KEY:
            raise ValueError("AWS_SECRET_ACCESS_KEY environment variable is required")
    
    def _retry_operation(self, operation, *args, **kwargs):
        """Retry S3 operations with exponential backoff."""
        last_exception = None
        
        for attempt in range(S3_RETRY_COUNT):
            try:
                return operation(*args, **kwargs)
            except ClientError as e:
                last_exception = e
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                logger.warning(f"S3 operation failed (attempt {attempt + 1}/{S3_RETRY_COUNT}): {error_code}")
                
                if attempt < S3_RETRY_COUNT - 1:
                    delay = S3_RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error in S3 operation: {e}")
                break
        
        raise last_exception
    
    def upload_file(self, local_path: Union[str, Path], s3_key: str) -> str:
        """
        Upload file to S3 and return the URL.
        
        Args:
            local_path: Path to local file
            s3_key: S3 key (path) for the uploaded file
            
        Returns:
            S3 URL of uploaded file
        """
        try:
            local_path = Path(local_path)
            
            if not local_path.exists():
                raise FileNotFoundError(f"Local file not found: {local_path}")
            
            logger.info(f"Uploading {local_path} to s3://{self.bucket}/{s3_key}")
            
            # Upload with retry
            self._retry_operation(
                self.s3.upload_file,
                str(local_path),
                self.bucket,
                s3_key
            )
            
            # Generate URL
            if AWS_ENDPOINT_URL:
                url = f"{AWS_ENDPOINT_URL}/{self.bucket}/{s3_key}"
            else:
                url = f"https://s3.{AWS_REGION}.amazonaws.com/{self.bucket}/{s3_key}"
            
            logger.info(f"Successfully uploaded to: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            raise
    
    def download_file(self, s3_key: str, local_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Download file from S3.
        
        Args:
            s3_key: S3 key of file to download
            local_path: Local path to save file (optional)
            
        Returns:
            Path to downloaded file
        """
        try:
            if local_path is None:
                # Generate temporary filename
                filename = Path(s3_key).name
                local_path = TEMP_PATH / filename
            
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Downloading s3://{self.bucket}/{s3_key} to {local_path}")
            
            # Download with retry
            self._retry_operation(
                self.s3.download_file,
                self.bucket,
                s3_key,
                str(local_path)
            )
            
            if not local_path.exists():
                raise RuntimeError(f"Download failed - file not created: {local_path}")
            
            logger.info(f"Successfully downloaded to: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download {s3_key}: {e}")
            raise
    
    def download_from_url(self, s3_url: str, local_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Download file from S3 URL.
        
        Args:
            s3_url: Full S3 URL (s3://bucket/key or https://...)
            local_path: Local path to save file (optional)
            
        Returns:
            Path to downloaded file
        """
        try:
            # Parse S3 URL to extract bucket and key
            if s3_url.startswith('s3://'):
                # s3://bucket/key format
                s3_parts = s3_url[5:].split('/', 1)
                if len(s3_parts) != 2:
                    raise ValueError(f"Invalid S3 URL format: {s3_url}")
                bucket, s3_key = s3_parts
                
                if bucket != self.bucket:
                    logger.warning(f"URL bucket ({bucket}) differs from configured bucket ({self.bucket})")
            
            elif 'amazonaws.com' in s3_url or AWS_ENDPOINT_URL in s3_url:
                # HTTP(S) URL format
                # Extract key from URL
                if f"/{self.bucket}/" in s3_url:
                    s3_key = s3_url.split(f"/{self.bucket}/", 1)[1]
                else:
                    raise ValueError(f"Cannot extract S3 key from URL: {s3_url}")
            
            else:
                raise ValueError(f"Unsupported URL format: {s3_url}")
            
            return self.download_file(s3_key, local_path)
            
        except Exception as e:
            logger.error(f"Failed to download from URL {s3_url}: {e}")
            raise
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for S3 object.
        
        Args:
            s3_key: S3 key of the object
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        try:
            url = self._retry_operation(
                self.s3.generate_presigned_url,
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for {s3_key}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise

# Global S3 client instance
_s3_client = None

def get_s3_client() -> S3Client:
    """Get global S3 client instance."""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client

# Convenience functions
def upload_audio_to_s3(local_path: Union[str, Path], prefix: str = "audio") -> str:
    """Upload audio file to S3 with timestamp prefix."""
    local_path = Path(local_path)
    timestamp = int(time.time())
    s3_key = f"{prefix}/{timestamp}_{local_path.name}"
    
    client = get_s3_client()
    return client.upload_file(local_path, s3_key)

def download_audio_from_s3(s3_url: str) -> Path:
    """Download audio file from S3 URL."""
    client = get_s3_client()
    return client.download_from_url(s3_url)

def upload_subtitles_to_s3(local_path: Union[str, Path]) -> str:
    """Upload subtitle file to S3."""
    return upload_audio_to_s3(local_path, "subtitles")

# Test function
if __name__ == "__main__":
    """Test S3 client functionality."""
    try:
        client = get_s3_client()
        logger.info("S3 client initialized successfully")
        
        # Test basic configuration
        logger.info(f"Bucket: {client.bucket}")
        logger.info(f"Region: {AWS_REGION}")
        
    except Exception as e:
        logger.error(f"S3 client test failed: {e}")
        sys.exit(1)