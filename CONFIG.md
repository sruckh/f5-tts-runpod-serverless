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

### Optional Configuration  
```bash
AWS_REGION=us-east-1                          # AWS region (default: us-east-1)
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 # GPU memory optimization
CUDA_VISIBLE_DEVICES=0                        # GPU device selection
HF_HOME=/app/models                           # HuggingFace cache directory
TRANSFORMERS_CACHE=/app/models                # Transformers model cache
```

### RunPod Auto-Provided
```bash
RUNPOD_AI_API_KEY                             # Auto-provided by RunPod
RUNPOD_ENDPOINT_ID                            # Auto-provided by RunPod  
```

## Application Configuration Constants

### Model Settings <!-- #model-config -->
- **Model Type**: `F5-TTS` (default model from official container)
- **Sample Rate**: `22050` Hz (fixed for F5-TTS)
- **Device**: Auto-detected (`cuda` if available, fallback to `cpu`)
- **Cache Directory**: `/app/models` (set via environment variables)

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
- **Word Timings**: `return_word_timings` (default: `true`)
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
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

### Container Security <!-- #container-security -->
- **Base Image**: Official F5-TTS container (maintained by SWivid team)
- **Dependencies**: Minimal additional packages (`runpod`, `boto3`, `requests`)
- **Network**: Outbound HTTPS for S3, no inbound requirements
- **GPU Access**: CUDA runtime access required

## Common Configuration Patterns

### Development Environment <!-- #dev-config -->
```bash
# Local testing with MinIO instead of S3
S3_BUCKET=test-bucket
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1
```

### Production Environment <!-- #prod-config -->
```bash
# Production with dedicated S3 bucket and IAM role
S3_BUCKET=f5tts-prod-storage
AWS_REGION=us-west-2
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024  # Larger allocation for production
```

### High-Volume Environment <!-- #high-volume-config -->
```bash
# Optimized for high request volume
S3_BUCKET=f5tts-enterprise
AWS_REGION=us-east-1                           # Same region as RunPod for lower latency
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048 # Maximum memory allocation
```

## Configuration Validation

### Startup Checks <!-- #startup-validation -->
The application validates configuration on startup:

1. **S3 Connection**: `s3_utils.py:12-22` - Tests S3 client initialization
2. **Model Loading**: `runpod-handler.py:37-65` - Validates F5-TTS model access  
3. **GPU Detection**: `runpod-handler.py:35` - Confirms CUDA availability

### Runtime Validation <!-- #runtime-validation -->
```python
# Configuration checks during request processing
def validate_request(job_input):
    # Text validation: runpod-handler.py:167-168
    # Voice file validation: runpod-handler.py:97-98  
    # S3 upload validation: s3_utils.py:46-48
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

**Performance Issues**
- Adjust `PYTORCH_CUDA_ALLOC_CONF` based on available GPU memory
- Monitor S3 transfer speeds (consider bucket region)
- Check RunPod worker scaling configuration

## Keywords <!-- #keywords -->
Environment variables, configuration, S3 setup, AWS credentials, RunPod deployment, GPU settings, model caching, performance tuning, security configuration, F5-TTS settings