# F5-TTS RunPod Project Structure

## Root Directory Files
```
/opt/docker/f5-tts/
├── runpod-handler.py           # Main serverless handler (544 lines)
├── s3_utils.py                 # S3 storage utilities
├── model_cache_init.py         # Model caching initialization
├── Dockerfile.runpod           # Docker build configuration
├── README.md                   # Project overview
├── API.md                     # API documentation
└── CLAUDE.md                  # Claude Code instructions
```

## Key Python Modules

### runpod-handler.py (Main Handler)
- **Data Models** (lines 17-29): Pydantic models for API responses
- **Job Management** (lines 30-32): In-memory job tracking
- **Model Loading** (lines 54-125): F5-TTS and vocoder initialization
- **TTS Processing** (lines 127-298): Core audio generation logic
- **RunPod Handler** (lines 300-454): API endpoint routing
- **Main Startup** (lines 455-544): S3 sync and server initialization

### s3_utils.py
- S3 client initialization with support for custom endpoints
- File upload/download utilities
- Model caching functions for cold start optimization

## Documentation Structure
- **CONDUCTOR.md**: Documentation framework reference
- **ARCHITECTURE.md**: System design (template)
- **BUILD.md**: Build instructions (template)
- **API.md**: Comprehensive API reference
- **CONTRIBUTING.md**: Development guidelines (template)