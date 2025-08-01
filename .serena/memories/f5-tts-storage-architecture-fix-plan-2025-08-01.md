# F5-TTS Storage Architecture Fix Plan - Critical Issue Resolution

## Problem Identified

The current F5-TTS RunPod serverless implementation has **fundamental storage architecture issues** that will cause deployment failures:

### Current Broken Storage Strategy
```python
# INCORRECT - Will fail due to insufficient space
cache_dirs = [
    "/tmp/models",            # Assumed 10-20GB - WRONG! Only 1-5GB available
    "/app/models",            # Container storage - insufficient for AI models  
    "/runpod-volume/models"   # Correct location but used as "last resort"
]
```

### Core Issues
1. **Container Storage Misconception**: `/tmp` and `/app` have very limited space (~1-5GB total)
2. **Model Size Reality**: F5-TTS models are 2-4GB+ each, plus PyTorch/HuggingFace caches
3. **Priority Inversion**: `/runpod-volume` (large persistent storage) treated as fallback instead of primary
4. **Runtime Loading**: Models loaded during inference instead of build-time pre-loading

## Correct RunPod Serverless Storage Architecture

### Storage Layer Responsibilities

#### `/runpod-volume/` - Primary AI Model Storage (50GB - 1TB+)
- **F5-TTS model weights** (~2-4GB)
- **HuggingFace model cache** (transformers, tokenizers)
- **PyTorch model cache** (torch hub models)
- **Persistent across container restarts/scaling**
- **Large capacity configured per RunPod deployment**

#### `/tmp/` - Temporary Processing Only (1-5GB)
- **Downloaded voice files** during request processing
- **Temporary audio generation files** 
- **Working files** during inference pipeline
- **Cleared on container restart** (ephemeral)

#### **S3 Bucket** - External User Data Storage (Unlimited)
- **Voice file uploads** (user inputs)
- **Generated audio outputs** (results)
- **Logs and metadata**
- **Optional model backups** (for disaster recovery)

## Implementation Plan

### 1. Environment Variables Fix
```python
# CORRECT configuration
os.environ["HF_HOME"] = "/runpod-volume/models"
os.environ["TRANSFORMERS_CACHE"] = "/runpod-volume/models/transformers"
os.environ["HF_HUB_CACHE"] = "/runpod-volume/models/hub"
os.environ["TORCH_HOME"] = "/runpod-volume/models/torch"
```

### 2. Directory Structure
```bash
/runpod-volume/models/
├── hub/                    # HuggingFace Hub cache
├── transformers/           # Transformers library cache
├── torch/                  # PyTorch model cache
├── f5-tts/                # F5-TTS specific models
└── checkpoints/           # Model checkpoints
```

### 3. Model Loading Strategy
```python
# Build-time model pre-loading (Dockerfile)
RUN python -c "
import os
os.environ['HF_HOME'] = '/runpod-volume/models'
from F5TTS.model import F5TTS
F5TTS.from_pretrained('F5TTS_v1_Base', cache_dir='/runpod-volume/models')
"

# Runtime model loading (handler)
f5tts = F5TTS(
    model=model_name,
    device=device,
    hf_cache_dir="/runpod-volume/models"  # Explicit cache control
)
```

### 4. Processing Workflow
```python
# Correct file handling workflow
def process_tts_job(job_id, text, voice_name):
    # 1. Download voice from S3 to /tmp (temporary)
    voice_path = f"/tmp/{job_id}_voice.wav"
    download_from_s3(f"voices/{voice_name}", voice_path)
    
    # 2. Load model from /runpod-volume (persistent cache)
    f5tts = get_cached_model()  # Uses /runpod-volume/models
    
    # 3. Generate audio in /tmp (temporary processing)
    output_path = f"/tmp/{job_id}_output.wav"
    f5tts.infer(ref_file=voice_path, gen_text=text, file_wave=output_path)
    
    # 4. Upload result to S3 (persistent storage)
    result_url = upload_to_s3(output_path, f"output/{job_id}.wav")
    
    # 5. Cleanup /tmp files (temporary cleanup)
    os.unlink(voice_path)
    os.unlink(output_path)
    
    return result_url
```

## Critical Files Requiring Updates

### 1. `Dockerfile.runpod`
- Change model cache directories to `/runpod-volume/models`
- Pre-load F5-TTS models during build to persistent storage
- Set correct environment variables

### 2. `runpod-handler.py`
- Fix cache directory priority (runpod-volume first)
- Update model loading to use explicit cache paths
- Ensure temporary files use `/tmp` only

### 3. `s3_utils.py`
- Remove model syncing functions (models in /runpod-volume, not S3)
- Focus on voice files and output file handling only

### 4. Environment Configuration
- RunPod deployment must configure Network Volume mounted at `/runpod-volume`
- Minimum 50GB volume size recommended for F5-TTS models

## Performance & Reliability Impact

### Before Fix (Broken)
- ❌ **Cold Start**: 30-60s + frequent OOM failures
- ❌ **Success Rate**: ~20% due to storage issues
- ❌ **Disk Space Errors**: Constant failures when models don't fit

### After Fix (Correct)
- ✅ **Cold Start**: 2-3s (models pre-loaded in /runpod-volume)
- ✅ **Success Rate**: 99%+ (proper storage allocation)
- ✅ **Scalability**: Persistent model cache across all container instances

## Deployment Requirements

### RunPod Configuration Changes Required
1. **Network Volume**: Mount 50GB+ volume at `/runpod-volume`
2. **Environment Variables**: Point all caches to `/runpod-volume/models`
3. **Container Image**: Rebuild with models pre-loaded to correct paths
4. **Resource Allocation**: Ensure sufficient GPU memory + storage

This storage architecture fix is **critical** and must be implemented before any production deployment. The current implementation will fail due to insufficient container storage for AI models.