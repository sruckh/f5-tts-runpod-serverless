# F5-TTS RunPod Serverless v3.0

**Complete architectural redesign** - Third restart with proper 2-layer architecture addressing all previous failures.

## Architecture Overview

### Layer 1: Slim Container (<2GB)
- **Purpose**: GitHub Actions buildable container
- **Contents**: Python 3.10-slim, RunPod handler, minimal dependencies
- **Constraints**: Must build successfully on GitHub Actions
- **Size Limit**: <2GB total

### Layer 2: Network Volume (/runpod-volume/f5tts/)
- **Purpose**: Heavy ML dependencies and model cache  
- **Contents**: Virtual environment, PyTorch, F5-TTS, WhisperX, models
- **Availability**: Runtime only (not during build)
- **Performance**: Warm loading for 1-3s inference

## Key Features

✅ **Constraint Compliant**: Respects container size and network volume timing  
✅ **Warm Loading**: Models persist in memory across requests  
✅ **Word-Level Timing**: WhisperX integration with forced alignment  
✅ **ASS Subtitles**: Professional subtitle generation  
✅ **S3 Integration**: Input/output audio file handling  
✅ **Error Resilient**: Comprehensive error handling and recovery  

## API Interface

```json
{
  "input": {
    "audio_url": "s3://bucket/input.wav",
    "voice_reference_url": "s3://bucket/reference.wav", 
    "text": "Text to synthesize",
    "options": {
      "create_subtitles": true,
      "subtitle_format": "ass"
    }
  }
}
```

## Project Structure

```
f5-tts/
├── Dockerfile                  # Slim container definition  
├── handler.py                 # RunPod serverless handler
├── requirements.txt           # Container dependencies (minimal)
├── runtime_requirements.txt   # Network volume dependencies (heavy ML)
├── src/
│   ├── setup_environment.py  # First-time environment setup
│   ├── f5tts_engine.py       # F5-TTS model management
│   ├── whisperx_engine.py    # WhisperX timing generation
│   ├── subtitle_generator.py # ASS subtitle creation
│   ├── s3_client.py          # S3 utilities  
│   └── config.py             # Configuration constants
├── scripts/
│   └── setup_runtime.sh      # Network volume setup
└── tests/
    └── test_handler.py       # Basic tests
```

## Deployment

1. **Build Container**: Builds on GitHub Actions (<2GB)
2. **Deploy to RunPod**: Container starts successfully  
3. **First Request**: Installs dependencies on network volume
4. **Subsequent Requests**: Uses cached models for 1-3s inference

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `S3_BUCKET` | S3 bucket for audio files | Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes |
| `AWS_REGION` | AWS region | Yes |
| `AWS_ENDPOINT_URL` | S3 endpoint URL | Optional |

## Error Recovery

- **Cold Start Failures**: Automatic retry with exponential backoff
- **Model Loading**: Graceful degradation and error reporting  
- **S3 Operations**: Retry logic with proper error handling
- **Memory Management**: Automatic cleanup and garbage collection

## Performance Targets

- **Cold Start**: <60s for first request (includes model downloads)
- **Warm Inference**: 1-3s for subsequent requests
- **Container Size**: <2GB for GitHub Actions builds  
- **Memory Usage**: Efficient model loading and caching

---

**Previous Versions**: 
- v1.0: Failed due to container size constraints (71 commits)
- v2.0: Failed due to architecture thrashing  
- v3.0: **Current** - Proper 2-layer architecture design# F5-TTS RunPod Serverless v3.0

**Complete architectural redesign** - Third restart with proper 2-layer architecture addressing all previous failures.

## Architecture Overview

### Layer 1: Slim Container (<2GB)
- **Purpose**: GitHub Actions buildable container
- **Contents**: Python 3.10-slim, RunPod handler, minimal dependencies
- **Constraints**: Must build successfully on GitHub Actions
- **Size Limit**: <2GB total

### Layer 2: Network Volume (/runpod-volume/f5tts/)
- **Purpose**: Heavy ML dependencies and model cache  
- **Contents**: Virtual environment, PyTorch, F5-TTS, WhisperX, models
- **Availability**: Runtime only (not during build)
- **Performance**: Warm loading for 1-3s inference

## Key Features

✅ **Constraint Compliant**: Respects container size and network volume timing  
✅ **Warm Loading**: Models persist in memory across requests  
✅ **Word-Level Timing**: WhisperX integration with forced alignment  
✅ **ASS Subtitles**: Professional subtitle generation  
✅ **S3 Integration**: Input/output audio file handling  
✅ **Error Resilient**: Comprehensive error handling and recovery  

## API Interface

```json
{
  "input": {
    "audio_url": "s3://bucket/input.wav",
    "voice_reference_url": "s3://bucket/reference.wav", 
    "text": "Text to synthesize",
    "options": {
      "create_subtitles": true,
      "subtitle_format": "ass"
    }
  }
}
```

## Project Structure

```
f5-tts/
├── Dockerfile                  # Slim container definition  
├── handler.py                 # RunPod serverless handler
├── requirements.txt           # Container dependencies (minimal)
├── runtime_requirements.txt   # Network volume dependencies (heavy ML)
├── src/
│   ├── setup_environment.py  # First-time environment setup
│   ├── f5tts_engine.py       # F5-TTS model management
│   ├── whisperx_engine.py    # WhisperX timing generation
│   ├── subtitle_generator.py # ASS subtitle creation
│   ├── s3_client.py          # S3 utilities  
│   └── config.py             # Configuration constants
├── scripts/
│   └── setup_runtime.sh      # Network volume setup
└── tests/
    └── test_handler.py       # Basic tests
```

## Deployment

1. **Build Container**: Builds on GitHub Actions (<2GB)
2. **Deploy to RunPod**: Container starts successfully  
3. **First Request**: Installs dependencies on network volume
4. **Subsequent Requests**: Uses cached models for 1-3s inference

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `S3_BUCKET` | S3 bucket for audio files | Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes |
| `AWS_REGION` | AWS region | Yes |
| `AWS_ENDPOINT_URL` | S3 endpoint URL | Optional |

## Error Recovery

- **Cold Start Failures**: Automatic retry with exponential backoff
- **Model Loading**: Graceful degradation and error reporting  
- **S3 Operations**: Retry logic with proper error handling
- **Memory Management**: Automatic cleanup and garbage collection

## Performance Targets

- **Cold Start**: <60s for first request (includes model downloads)
- **Warm Inference**: 1-3s for subsequent requests
- **Container Size**: <2GB for GitHub Actions builds  
- **Memory Usage**: Efficient model loading and caching

---

**Previous Versions**: 
- v1.0: Failed due to container size constraints (71 commits)
- v2.0: Failed due to architecture thrashing  
- v3.0: **Current** - Proper 2-layer architecture design