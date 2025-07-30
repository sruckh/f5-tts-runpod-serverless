# Conversation Handoff: Flash Attention & RunPod Fixes - 2025-07-30

## Current Status: IN PROGRESS
**Priority**: HIGH - User experiencing deployment issues on RunPod

## Problem Summary
User experiencing two critical issues with F5-TTS RunPod serverless deployment:

### Issue 1: Flash Attention Wheel Compatibility ✅ FIXED
- **Problem**: `flash_attn-2.8.2+cu12torch2.4cxx11abiFALSE-cp310-cp310-linux_x86_64.whl is not a supported wheel on this platform`
- **Root Cause**: Container uses Python 3.11, but code was trying to install Python 3.10 wheels with wrong torch version
- **Solution**: Updated `model_cache_init.py:install_flash_attn()` with:
  - Dynamic Python version detection (`sys.version_info`)
  - Correct wheel URLs: Python 3.11 uses `torch2.6`, Python 3.10 uses `torch2.4`
  - Broader CUDA 12.x matching (not just 12.4)
  - Multi-tier fallback strategy (wheel → source installation)

### Issue 2: CUDA Memory Configuration ✅ IDENTIFIED
- **Problem**: `RuntimeError: Unrecognized CachingAllocator option: ax_split_size_mb`
- **Root Cause**: User setting `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024` but "m" getting truncated to "ax_split_size_mb"
- **Solution**: User needs to set environment variable in RunPod interface WITHOUT quotes:
  - Variable: `PYTORCH_CUDA_ALLOC_CONF`
  - Value: `max_split_size_mb:1024` (no quotes - RunPod handles quoting)

## Technical Implementation Completed

### File Modified: `model_cache_init.py`
**Function**: `install_flash_attn()` (lines 78-127) - completely rewritten

**Key Changes**:
- Added Python version detection: `python_version = f"{sys.version_info.major}.{sys.version_info.minor}"`
- Correct wheel mapping:
  - Python 3.11 + CUDA 12.x: `flash_attn-2.8.2+cu12torch2.6cxx11abiFALSE-cp311-cp311-linux_x86_64.whl`
  - Python 3.10 + CUDA 12.x: `flash_attn-2.8.2+cu12torch2.4cxx11abiFALSE-cp310-cp310-linux_x86_64.whl`
  - Python 3.9 + CUDA 12.x: `flash_attn-2.8.2+cu12torch2.4cxx11abiFALSE-cp39-cp39-linux_x86_64.whl`
- Improved CUDA version matching (any 12.x, not just 12.4)
- Enhanced error handling and fallback strategies
- Better logging with Python/CUDA version detection

### Critical Discovery
User found correct wheel URL: `https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.2/flash_attn-2.8.2+cu12torch2.6cxx11abiFALSE-cp311-cp311-linux_x86_64.whl`

Key insight: Python 3.11 wheels use `torch2.6`, not `torch2.4`

## Current Todo Status
- ✅ Fix flash_attn Python version compatibility with correct torch2.6 wheels for Python 3.11
- ✅ Fix PYTORCH_CUDA_ALLOC_CONF typo: User needs to set env var in RunPod without quotes
- ⏳ PENDING: Add environment variable validation in startup script to catch configuration issues

## Next Steps for Continuation
1. **User Action Required**: Update RunPod environment variable `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024` (no quotes)
2. **Test Deployment**: User should redeploy container to test both fixes
3. **Optional Enhancement**: Consider adding environment variable validation in startup script
4. **Monitor Results**: Check if both flash_attn installation and CUDA memory allocation work correctly

## Error Logs Context
**Original Error Log**:
```
🎯 Detected CUDA version: 12.4
⚡ Installing CUDA 12.4 compatible flash_attn...
❌ flash_attn installation failed: ERROR: flash_attn-2.8.2+cu12torch2.4cxx11abiFALSE-cp310-cp310-linux_x86_64.whl is not a supported wheel on this platform.
...
❌ Error loading F5-TTS model: Unrecognized CachingAllocator option: ax_split_size_mb
```

## Project Context
- **Base Image**: `ghcr.io/swivid/f5-tts:main` (Python 3.11)
- **Deployment**: RunPod serverless with CUDA 12.4
- **Purpose**: F5-TTS text-to-speech API with voice cloning
- **Previous Work**: Flash attention architecture correction, voice transcription conversion completed

## Files Ready for Testing
- `model_cache_init.py` - Updated with fixed flash_attn installation
- Container image should work with Python 3.11 + CUDA 12.x after user sets correct env var

## Success Criteria
1. Flash_attn installs successfully with correct Python 3.11 wheel
2. CUDA memory allocator accepts max_split_size_mb:1024 configuration
3. F5-TTS model loads without errors
4. RunPod serverless deployment completes successfully

The implementation is ready - waiting for user to test with corrected environment variable.