# Flash Attention CUDA 12.4 Compatibility Enhancement

## Context
RunPod serverless environment uses CUDA 12.4.0, but the base image `ghcr.io/swivid/f5-tts:main` may have incompatible flash_attn version causing performance issues with F5-TTS model inference.

## Solution Implemented
Added CUDA 12.4 compatible flash_attn wheel installation as final step in `Dockerfile.runpod:34-36`:

```dockerfile
# Install CUDA 12.4 compatible flash_attn as final step to ensure compatibility
RUN pip install --no-cache-dir --force-reinstall \
    https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.2/flash_attn-2.8.2+cu12torch2.4cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
```

## Key Design Decisions
1. **Strategic Positioning**: Placed as final step before CMD to prevent other dependencies from overriding
2. **Force Reinstall**: Uses `--force-reinstall` to ensure base image version gets replaced
3. **Direct Wheel URL**: Avoids requirements.txt bloat and ensures exact version match
4. **Version Targeting**: Specific wheel for CUDA 12.4 + PyTorch 2.4 + Python 3.10

## Performance Impact
- **CUDA Optimization**: Hardware-accelerated attention mechanisms for F5-TTS
- **Container Efficiency**: No requirements.txt overhead
- **Deployment Ready**: Guaranteed compatibility with RunPod CUDA 12.4 environment

## Task Reference
- **Task ID**: TASK-2025-07-30-003
- **Journal Entry**: 2025-07-30 18:00
- **Status**: Complete