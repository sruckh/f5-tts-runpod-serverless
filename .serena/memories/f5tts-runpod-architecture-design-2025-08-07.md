# F5-TTS RunPod Serverless Architecture - Final Design 2025-08-07

## Executive Summary
Complete architectural redesign for F5-TTS RunPod serverless deployment, addressing all failures from the previous 71-commit cycle through proper constraint understanding and 2-layer architecture approach.

## Core Architecture: 2-Layer Design

### Layer 1: Slim Container (<2GB)
**Purpose**: GitHub Actions buildable container with minimal dependencies
**Contents**:
- Python 3.10-slim base image
- RunPod serverless library
- Basic system libraries (ca-certificates, curl)
- Handler entry point script
- S3 client utilities (boto3)
- **NO ML dependencies** (PyTorch, F5-TTS, WhisperX)

### Layer 2: Network Volume Runtime (/runpod-volume/f5tts/)
**Purpose**: Heavy ML dependencies and model cache
**Structure**:
```
/runpod-volume/f5tts/
├── venv/                    # Virtual environment (isolated)
├── models/                  # Model cache (persistent)
│   ├── f5-tts/
│   │   ├── F5TTS_Base/     # Base F5-TTS model  
│   │   └── E2TTS_Base/     # E2 TTS model
│   └── whisperx/
│       ├── large-v2/       # Whisper model
│       └── align_models/   # Wav2Vec2 alignment models
├── temp/                   # Temporary processing files
├── logs/                   # Runtime logs
├── cache/                  # Download cache
└── setup_complete.flag     # Setup completion marker
```

## Technical Specifications

### Dependencies
**Container (minimal)**:
- Python 3.10.x
- runpod>=1.2.0  
- boto3 (S3 integration)
- requests, json

**Network Volume (runtime)**:
- torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu126
- flash-attention: https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.0.post2/flash_attn-2.8.0.post2+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
- whisperx
- F5-TTS (from GitHub)
- python-ass (subtitle generation)

### Request Flow
1. **Cold Start (First Request)**:
   - Check `/runpod-volume/f5tts/setup_complete.flag`
   - If not exists: Execute full runtime setup
   - Create virtual environment
   - Install ML dependencies 
   - Download and cache models
   - Mark setup complete

2. **Warm Loading (Subsequent Requests)**:
   - Activate existing virtual environment
   - Load cached models (stay in memory)
   - Process with 1-3s inference time

### API Interface
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

{
  "output": {
    "audio_url": "s3://bucket/output.wav",
    "subtitles_url": "s3://bucket/output.ass",
    "word_timings": [...],
    "processing_time": 2.1
  }
}
```

## Implementation Components

### Core Files
1. **handler.py** - RunPod serverless entry point
2. **Dockerfile** - Slim container definition
3. **requirements.txt** - Container dependencies (minimal)
4. **runtime_requirements.txt** - Network volume dependencies

### Source Modules
- **setup_environment.py** - First-time environment setup
- **f5tts_engine.py** - F5-TTS model management and inference
- **whisperx_engine.py** - WhisperX word-level timing
- **subtitle_generator.py** - ASS subtitle creation
- **s3_client.py** - S3 upload/download utilities
- **config.py** - Configuration constants

## Constraint Compliance

### GitHub Actions Build
- Container size <2GB (verified with slim base + minimal deps)
- No network volume access during build
- Proper syntax and dependency resolution

### RunPod Serverless
- Network volume available only at runtime
- Container reuse enables warm loading
- CUDA pre-installed in RunPod environment
- Virtual environment isolation prevents conflicts

### Performance Requirements  
- 1-3s inference through warm loading
- Model persistence across requests
- Efficient memory management
- Progressive loading strategy

## Risk Mitigation

### Lessons from 71-Commit Failure
- **Architecture Thrashing**: Fixed with systematic 2-layer approach
- **Constraint Misunderstanding**: Proper network volume timing
- **Performance Regression**: Warm loading maintained throughout
- **Symptom Chasing**: Incremental validation prevents cascade failures

### Error Handling Strategy
- Graceful degradation on model load failures
- Comprehensive logging and error reporting
- Automatic retry logic for network operations
- Proper cleanup of temporary resources
- Memory management and garbage collection

## Implementation Phases

### Phase 1: Foundation (Validate Container)
- Create Dockerfile and basic handler
- Test GitHub Actions build success  
- Test container startup (no exit code 1)
- No ML dependencies yet

### Phase 2: Network Volume Setup
- Environment setup and venv creation
- Test /runpod-volume access
- Validate Python path resolution

### Phase 3: PyTorch Integration
- Install PyTorch 2.6.0 + flash-attention
- Test CUDA availability
- Validate memory usage

### Phase 4: F5-TTS Integration  
- Model installation and caching
- Test inference performance
- Validate 1-3s target

### Phase 5: WhisperX Integration
- Audio processing and timing
- Word-level alignment testing
- Accuracy validation  

### Phase 6: Complete Pipeline
- S3 integration testing
- ASS subtitle generation
- End-to-end validation

## Success Criteria
1. Container builds successfully on GitHub Actions
2. Container starts without errors (no exit code 1)
3. F5-TTS inference achieves 1-3s performance
4. WhisperX provides accurate word-level timings
5. ASS subtitles generate correctly
6. S3 integration works reliably
7. System handles cold start and warm loading properly
8. Memory usage stays within RunPod limits

This architecture design completely addresses the failures of the previous implementation and provides a solid foundation for successful F5-TTS RunPod serverless deployment.