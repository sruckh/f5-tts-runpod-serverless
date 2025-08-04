# Runtime Configuration

## Critical Context (Read First)
- **Tech Stack**: F5-TTS RunPod Serverless with S3 storage
- **Main File**: `runpod-handler.py` 
- **Core Mechanic**: Official F5-TTS container + minimal wrapper for serverless deployment
- **Key Integration**: S3 for model/voice/output storage, RunPod for GPU compute
- **Platform Support**: RunPod serverless endpoints with GPU support
- **Container Base**: `ghcr.io/swivid/f5-tts:main` (official F5-TTS container)

## Environment Variables

### Required S3 Configuration
```bash
S3_BUCKET=your-bucket-name                    # S3 bucket for models/voices/outputs
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE        # AWS access key with S3 permissions  
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG   # AWS secret key
```

### S3 Model Caching (Cold Start Optimization)
```bash
ENABLE_S3_MODEL_CACHE=true                    # Enable S3 model caching (default: true)
```
**Benefits**: 
- **Faster Cold Starts**: Models download from S3 instead of HuggingFace (~10x faster)
- **Reliable Storage**: Models persist across RunPod instances and container restarts
- **Cost Effective**: Reduced bandwidth costs from repeated HuggingFace downloads
- **Automatic Sync**: Models auto-upload to S3 after first download

### S3-Compatible Services (Backblaze B2, DigitalOcean Spaces, etc.)
```bash
AWS_ENDPOINT_URL=https://s3.us-west-001.backblazeb2.com  # Custom S3 endpoint URL
```

### Timing Extraction APIs (Word-Level Timing)

#### WhisperX (Primary Method - Installed at Runtime)
```bash
# No additional environment variables required
# WhisperX is automatically installed during container startup
```
**Purpose**: Primary method for word-level timing generation when `return_word_timings: true`
**Cost**: Free (runs locally on GPU)
**Features**: 
- Superior timing accuracy through forced alignment
- Multi-language support with automatic detection
- Offline processing (no API calls required)
- Languages: English, French, German, Spanish, Italian, Japanese, Chinese, Dutch

#### Google Cloud Speech-to-Text API (Fallback Method)
```bash
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}  # Service account JSON content (RECOMMENDED)
# OR
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json          # Service account JSON file path
GOOGLE_CLOUD_PROJECT=your-project-id                                  # Google Cloud project ID (optional)
```
**Purpose**: Fallback method for word-level timing when WhisperX fails
**Cost**: ~$0.012 per request when timing is enabled
**Features**: 
- Nanosecond-precision word timestamps
- Confidence scoring for timing accuracy
- Automatic punctuation and formatting
- Enterprise-grade reliability

### Optional Configuration  
```bash
AWS_REGION=us-east-1                          # AWS region (default: us-east-1)
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 # GPU memory optimization
CUDA_VISIBLE_DEVICES=0                        # GPU device selection
# HF_HOME - Set dynamically during startup (S3 cache > RunPod volume > local)
# TRANSFORMERS_CACHE - Set dynamically during startup 
# HF_HUB_CACHE - Set dynamically during startup
# TORCH_HOME - Set dynamically during startup
```

### RunPod Auto-Provided
```bash
RUNPOD_AI_API_KEY                             # Auto-provided by RunPod
RUNPOD_ENDPOINT_ID                            # Auto-provided by RunPod  
```

## Runtime Installation Architecture

### Heavy Dependencies Installed at Runtime <!-- #runtime-installation -->
The system now uses a **runtime installation architecture** where heavy modules are installed during container startup rather than build time:

**Modules Installed at Runtime**:
- `flash_attn` - GPU-optimized attention mechanisms (CUDA 12.x wheel)
- `transformers>=4.48.1` - Hugging Face transformers library
- `google-cloud-speech` - Google Cloud Speech-to-Text API client
- `whisperx` - WhisperX for advanced word-level timing

**Benefits**:
- **Smaller Base Container**: ~60% reduction in container image size
- **Faster Cold Starts**: Essential dependencies only in base image
- **Better Reliability**: Runtime installation with proper error handling
- **Flexible Configuration**: Install only needed components based on request

**Installation Process**:
```python
# runpod-handler.py lines 60-104
# Each module checks if already available before installation
# Uses subprocess.check_call for reliable installation
# Proper error handling and status reporting
```

## Application Configuration Constants

### Model Settings <!-- #model-config -->
- **Model Type**: `F5-TTS` (default model from official container)
- **Sample Rate**: `22050` Hz (fixed for F5-TTS)
- **Device**: Auto-detected (`cuda` if available, fallback to `cpu`)
- **Cache Directory**: Dynamic (S3 cache > RunPod volume > local fallback)

### Performance Tuning Settings <!-- #performance-config -->
```python
# runpod-handler.py lines 35-55
PYTORCH_CUDA_ALLOC_CONF = "max_split_size_mb:512"  # Prevents GPU memory fragmentation
REQUEST_TIMEOUT = 30                                # HTTP request timeout (seconds)
PROCESSING_TIMEOUT = 300                           # TTS processing timeout (seconds)
```

### S3 Storage Configuration <!-- #s3-config -->
```python
# s3_utils.py lines 6-9
S3_BUCKET = os.environ.get("S3_BUCKET")            # Required: bucket name
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")  # Default region
CONTENT_TYPE = "audio/wav"                         # Audio file MIME type
```

## Feature Flags

### Audio Processing <!-- #audio-flags -->
- **Word Timings**: `return_word_timings` (default: `false`)
- **Timing Method**: `timing_method` parameter ("whisperx" default, "google" fallback)
- **Timing Format**: `timing_format` parameter ("srt", "vtt", "csv", "json", "ass")
- **Speed Control**: `speed` parameter (range: 0.5-2.0, default: 1.0)
- **Voice Cloning**: `local_voice` parameter (optional)

### API Endpoints <!-- #endpoint-flags -->
- **TTS Generation**: Default endpoint (no `endpoint` parameter)
- **Voice Upload**: `endpoint: "upload"`
- **Job Status**: `endpoint: "status"`  
- **Result Retrieval**: `endpoint: "result"`

## Security Configuration

### S3 Permissions Required <!-- #s3-permissions -->
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

### Google Cloud IAM Permissions Required <!-- #google-cloud-permissions -->
```json
{
  "name": "F5-TTS Speech-to-Text Role",
  "includedPermissions": [
    "speech.operations.get",
    "speech.speech.recognize",
    "speech.speech.longrunningrecognize"
  ]
}
```

**Service Account Setup**:
1. Create Google Cloud project or use existing
2. Enable Cloud Speech-to-Text API
3. Create service account with Speech-to-Text permissions
4. Download service account JSON key file
5. Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

### Container Security <!-- #container-security -->
- **Base Image**: Official F5-TTS container (maintained by SWivid team)
- **Dependencies**: Minimal additional packages (`runpod`, `boto3`, `requests`, `google-cloud-speech`)
- **Network**: Outbound HTTPS for S3 and Google Cloud APIs, no inbound requirements
- **GPU Access**: CUDA runtime access required
- **API Keys**: Google Cloud service account JSON stored securely in environment

## Common Configuration Patterns

### Development Environment <!-- #dev-config -->
```bash
# Local testing with MinIO instead of S3
S3_BUCKET=test-bucket
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1

# Google Cloud for timing (development project)
GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-dev.json
GOOGLE_CLOUD_PROJECT=f5tts-dev-project
```

### Production Environment <!-- #prod-config -->
```bash
# Production with dedicated S3 bucket and IAM role
S3_BUCKET=f5tts-prod-storage
AWS_REGION=us-west-2
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024  # Larger allocation for production

# Google Cloud for timing (production project)
GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-prod.json
GOOGLE_CLOUD_PROJECT=f5tts-production
```

### High-Volume Environment <!-- #high-volume-config -->
```bash
# Optimized for high request volume
S3_BUCKET=f5tts-enterprise
AWS_REGION=us-east-1                           # Same region as RunPod for lower latency
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048 # Maximum memory allocation

# Google Cloud for timing (enterprise project with quotas)
GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-enterprise.json
GOOGLE_CLOUD_PROJECT=f5tts-enterprise
```

## Configuration Validation

### Startup Checks <!-- #startup-validation -->
The application validates configuration on startup:

1. **S3 Connection**: `s3_utils.py:12-22` - Tests S3 client initialization
2. **Model Loading**: `runpod-handler.py:37-65` - Validates F5-TTS model access  
3. **GPU Detection**: `runpod-handler.py:35` - Confirms CUDA availability
4. **Google Cloud Speech API**: `runpod-handler.py:231-293` - Validates service account credentials and API access

### Runtime Validation <!-- #runtime-validation -->
```python
# Configuration checks during request processing
def validate_request(job_input):
    # Text validation: runpod-handler.py:167-168
    # Voice file validation: runpod-handler.py:97-98  
    # S3 upload validation: s3_utils.py:46-48
    # Google Speech API validation: runpod-handler.py:231-293
```

## Troubleshooting Configuration

### Common Issues <!-- #config-troubleshooting -->

**S3 Connection Failed**
- Verify `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` are set
- Check IAM permissions for S3 bucket access
- Confirm AWS region matches bucket region

**Model Loading Failed**  
- Check GPU availability with `nvidia-smi`  
- Verify HuggingFace cache directory is writable
- Monitor memory usage during model loading

**WhisperX Runtime Installation Failed**
- Check GPU availability and CUDA compatibility
- Verify sufficient disk space for model downloads (~2GB)
- Monitor container startup logs for installation errors
- Ensure internet connectivity for model downloads
- Check GPU memory (minimum 4GB recommended)

**Google Cloud Speech API Failed**
- Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid service account JSON
- Check Google Cloud project has Speech-to-Text API enabled
- Confirm service account has required IAM permissions
- Validate Google Cloud project billing is enabled
- Monitor API quotas and usage limits in Google Cloud Console

**Performance Issues**
- Adjust `PYTORCH_CUDA_ALLOC_CONF` based on available GPU memory
- Monitor S3 transfer speeds (consider bucket region)
- Check RunPod worker scaling configuration
- Monitor Google Speech API latency and quotas for timing requests

## Keywords <!-- #keywords -->
Environment variables, configuration, S3 setup, AWS credentials, RunPod deployment, GPU settings, model caching, performance tuning, security configuration, F5-TTS settings, Google Cloud Speech-to-Text, WhisperX, word timing, subtitle generation, service account, IAM permissions, speech recognition, timing accuracy, FFMPEG integration, runtime installation, forced alignment, multi-language support, timing method, fallback mechanism, container optimization