# ARCHITECTURE.md

## Tech Stack
- **Framework**: F5-TTS (PyTorch-based text-to-speech model)
- **Runtime**: Python 3.9+ with CUDA support
- **Storage**: S3-compatible object storage (AWS S3, Backblaze B2)
- **Infrastructure**: RunPod Serverless GPU infrastructure
- **Containerization**: Docker with NVIDIA GPU support
- **Build Tools**: Docker multi-stage builds, pip, conda

## Directory Structure
```
f5-tts/
├── runpod-handler.py       # Main serverless handler
├── s3_utils.py            # S3 storage utilities  
├── Dockerfile.runpod      # Production container definition
├── convert_transcriptions.py  # Audio transcription utilities
├── validate-storage-config.py  # Storage validation script
├── Voices/                # Sample voice files and transcriptions
│   ├── *.wav             # Reference audio files
│   ├── *.txt             # Transcription text files
│   └── *.csv             # Processed timing data
├── PLAYBOOKS/
│   └── DEPLOY.md          # Deployment procedures
└── docs/                  # Documentation files
    ├── API.md
    ├── BUILD.md
    └── *.md
```

## Key Architectural Decisions

### Serverless Architecture Pattern
**Context**: Previous threading-based implementation failed due to RunPod serverless constraints
**Decision**: Synchronous processing with immediate result return
**Rationale**: RunPod serverless functions are stateless and don't support background threading
**Consequences**: Simpler API, faster responses, but processing must complete within request timeout

### Model Pre-loading Strategy  
**Context**: Runtime model downloads caused 30-60s cold starts and disk space failures
**Decision**: Pre-load F5-TTS models during container build
**Rationale**: Trade container size for performance and reliability
**Consequences**: Larger container images (~8GB) but sub-3s cold starts and 99% reliability

### S3 Storage Integration
**Context**: Serverless functions have limited local storage and no persistence
**Decision**: Use S3-compatible storage for all persistent data
**Rationale**: Scalable, durable storage that persists across function invocations
**Consequences**: Network dependency for file operations, but enables stateless architecture

### Flash Attention Optimization
**Context**: Standard attention mechanisms were too slow for real-time inference
**Decision**: Use flash_attn library for optimized attention computation
**Rationale**: 2-3x speed improvement in attention layers critical for TTS quality
**Consequences**: Complex build process but significant performance gains

## Component Architecture

### RunPod Handler Structure <!-- #runpod-handler -->
```python
# Main serverless entry point (lines 1-50)
def handler(event):                    # <!-- #handler-main -->
    """Primary serverless function entry point"""
    pass

# Endpoint routing (lines 51-100)  
def route_endpoint(endpoint, input_data):  # <!-- #endpoint-router -->
    """Route requests to appropriate handlers"""
    pass

# TTS generation (lines 101-200)
def generate_tts(text, voice, speed):  # <!-- #tts-generator -->
    """Core F5-TTS inference functionality"""
    pass

# Voice management (lines 201-250)
def upload_voice(voice_data):          # <!-- #voice-uploader -->
    """Handle voice file uploads and processing"""
    pass
```

### S3 Utilities Structure <!-- #s3-utils -->
```python
# S3 client initialization (lines 1-30)
def get_s3_client():                   # <!-- #s3-client -->
    """Initialize S3 client with configuration"""
    pass

# File operations (lines 31-100)
def upload_file(local_path, s3_key):   # <!-- #s3-upload -->
    """Upload files to S3 with error handling"""
    pass

def download_file(s3_key, local_path): # <!-- #s3-download -->
    """Download files from S3 with caching"""
    pass
```

## System Flow Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                    REQUEST PROCESSING                       │
│                                                             │
│ [RunPod API] ──→ [Handler] ──→ [Endpoint Router]           │
│                      │              │                       │
│                      │              ├─→ [TTS Generator]     │
│                      │              ├─→ [Voice Uploader]    │
│                      │              ├─→ [Voice Lister]      │
│                      │              └─→ [File Downloader]   │
│                      │                                      │
│                      ▼                                      │
│              [Result Handler] ──→ [Response]                │
└─────────────────────────────────────────────────────────────┘
                      │                      │
                      ▼                      ▼
          ┌─────────────────────┐    ┌─────────────────────┐
          │    S3 STORAGE       │    │   LOCAL PROCESSING  │
          │                     │    │                     │
          │ voices/             │    │ /tmp/models/        │
          │ output/             │    │ /tmp/voices/        │
          │ timings/            │    │ /tmp/output/        │
          └─────────────────────┘    └─────────────────────┘
```

## Performance Characteristics

### Timing Benchmarks
| Operation | Cold Start | Warm Start | Target |
|-----------|------------|-------------|--------|
| Container Init | 2-3s | 0.1s | <5s |
| Model Loading | Pre-loaded | 0.1s | <1s |
| TTS Generation | 1-2s/10 words | 0.5-1s/10 words | <2s |
| S3 Upload | 0.2-1s | 0.2-1s | <2s |

### Resource Usage
- **GPU Memory**: 4-6GB (F5-TTS model + flash_attn)
- **System Memory**: 8-12GB
- **Storage**: 8-10GB container image, 2-5GB runtime temp files
- **Network**: High bandwidth required for S3 operations

## Common Patterns

### Error Handling Pattern
**When to use**: All external API calls and file operations
**Implementation**: 
```python
try:
    result = risky_operation()
    return {"status": "success", "data": result}
except Exception as e:
    logger.error(f"Operation failed: {str(e)}")
    return {"error": f"Operation failed: {str(e)}"}
```

### S3 File Operations Pattern
**When to use**: Any file upload/download operations
**Implementation**:
```python
def safe_s3_operation(operation_func, *args, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

### Model Caching Pattern
**When to use**: Heavy model initialization operations
**Implementation**:
```python
_model_cache = {}

def get_model(model_name):
    if model_name not in _model_cache:
        _model_cache[model_name] = load_model(model_name)
    return _model_cache[model_name]
```

### Request Validation Pattern
**When to use**: All endpoint handlers
**Implementation**:
```python
def validate_input(input_data, required_fields):
    for field in required_fields:
        if field not in input_data:
            raise ValueError(f"Missing required field: {field}")
    return True
```

## Security Considerations

### Input Validation
- All text inputs sanitized and length-limited
- File uploads validated for type and size
- URL downloads restricted to HTTPS and size-limited

### Storage Security
- S3 bucket permissions configured for least privilege
- Generated files use UUID-based naming to prevent guessing
- Temporary files cleaned up after processing

### API Security
- RunPod API key authentication required
- Rate limiting enforced at infrastructure level
- Error messages sanitized to prevent information leakage

## Keywords <!-- #keywords -->
F5-TTS, RunPod, serverless, text-to-speech, TTS, voice cloning, PyTorch, CUDA, S3, container, Docker, flash attention, synchronous processing, model pre-loading, GPU inference, architecture, system design, tech stack, components, patterns