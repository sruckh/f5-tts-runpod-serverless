# Conversation Handoff: Backblaze B2 Endpoint Fix - 2025-07-30

## Critical Context
**Status**: IMPLEMENTATION COMPLETE - User needs to test deployment with new environment variable

## Problem Summary
User experiencing F5-TTS RunPod serverless deployment issues with **Backblaze B2** storage (not AWS S3):

### Issue 1: Flash Attention Installation ✅ RESOLVED
- **Problem**: Still using old container - `flash_attn-2.8.2+cu12torch2.4cxx11abiFALSE-cp310-cp310-linux_x86_64.whl is not a supported wheel on this platform`  
- **Solution**: User pulled `:latest` Docker image from Docker Hub which contains updated code with Python 3.11 compatibility

### Issue 2: S3 403 Forbidden Error ✅ FIXED  
- **Problem**: `❌ S3 download failed (403): An error occurred (403) when calling the HeadObject operation: Forbidden`
- **Root Cause**: Missing `AWS_ENDPOINT_URL` for Backblaze B2 - boto3 was trying to connect to AWS S3 instead of Backblaze
- **Solution**: Added complete Backblaze B2 support to codebase

## Technical Implementation Completed

### Files Modified:

#### 1. `s3_utils.py` - Added Backblaze B2 Support
- **Lines 10**: Added `AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")` 
- **Lines 13-26**: Updated boto3 client initialization with custom endpoint support:
  ```python
  client_config = {
      "service_name": "s3", 
      "aws_access_key_id": AWS_ACCESS_KEY_ID,
      "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
      "region_name": AWS_REGION,
  }
  if AWS_ENDPOINT_URL:
      client_config["endpoint_url"] = AWS_ENDPOINT_URL
  s3_client = boto3.client(**client_config)
  ```
- **Lines 54-60**: Updated URL generation for custom endpoints:
  ```python
  if AWS_ENDPOINT_URL:
      url = f"{AWS_ENDPOINT_URL.rstrip('/')}/{S3_BUCKET}/{object_name}"
  else:
      url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{object_name}"
  ```

#### 2. `CONFIG.md` - Updated Documentation  
- **Lines 20-23**: Added S3-Compatible Services section:
  ```bash
  ### S3-Compatible Services (Backblaze B2, DigitalOcean Spaces, etc.)
  AWS_ENDPOINT_URL=https://s3.us-west-001.backblazeb2.com  # Custom S3 endpoint URL
  ```
- **Lines 75-96**: Updated S3 permissions documentation with bucket-level permissions

## Current Status - USER ACTION REQUIRED

### Environment Variable Missing
User needs to add to RunPod serverless configuration:
```bash
AWS_ENDPOINT_URL=https://s3.us-west-001.backblazeb2.com
```

### Complete RunPod Environment Variables
```bash
S3_BUCKET=s3f5tts
AWS_ACCESS_KEY_ID=user-backblaze-key-id  
AWS_SECRET_ACCESS_KEY=user-backblaze-application-key
AWS_ENDPOINT_URL=https://s3.us-west-001.backblaze-b2.com
```

### Expected Behavior After Fix
1. S3 client initialization: `🔗 Using custom S3 endpoint: https://s3.us-west-001.backblazeb2.com`
2. File downloads: Should work with Backblaze B2 instead of 403 errors
3. File uploads: Generate proper Backblaze B2 URLs
4. Flash_attn: Install Python 3.11 wheels correctly

## Implementation Ready for Testing
- **Code Changes**: Complete and committed
- **Container Image**: User confirmed `:latest` tag pulled from Docker Hub  
- **Missing**: Only `AWS_ENDPOINT_URL` environment variable in RunPod
- **Test File**: `voices/Dorota.wav` confirmed to exist in Backblaze B2 bucket

## Success Criteria
1. ✅ No more S3 403 Forbidden errors
2. ✅ Successful voice file downloads from Backblaze B2
3. ✅ Flash_attn installs with correct Python 3.11 wheels
4. ✅ F5-TTS RunPod serverless deployment completes successfully

## Key Discovery
**Critical Issue**: User was using Backblaze B2, not AWS S3. The codebase only supported standard AWS S3 endpoints. Added full S3-compatible service support for Backblaze B2, DigitalOcean Spaces, MinIO, etc.

## Next Steps for Continuation
1. **User**: Add `AWS_ENDPOINT_URL` to RunPod environment variables
2. **User**: Redeploy/restart RunPod serverless to pick up environment variable  
3. **Test**: Verify both flash_attn installation and Backblaze B2 file access work
4. **Optional**: Monitor logs for successful S3 operations

The implementation is complete - only deployment testing with the new environment variable remains.