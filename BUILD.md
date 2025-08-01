# BUILD.md

## Prerequisites

### System Requirements
- **NVIDIA GPU**: 8GB+ VRAM (RTX 3080 or better recommended)
- **CUDA**: Version 11.8+ or 12.x
- **Docker**: With NVIDIA container runtime
- **Storage**: 15-20GB available space
- **Memory**: 16GB+ system RAM

### Development Tools
- **Docker**: Latest stable version
- **Git**: For repository management
- **Python**: 3.9+ (for local development)
- **CUDA Toolkit**: For local development

## Build Commands

### Production Container
```bash
# Build optimized RunPod container
docker build -f Dockerfile.runpod -t f5-tts-serverless:latest .

# Build with specific tag
docker build -f Dockerfile.runpod -t your-registry/f5-tts:v1.0.0 .

# Multi-platform build (if needed)
docker buildx build --platform linux/amd64 -f Dockerfile.runpod -t f5-tts-serverless:latest .
```

### Development Container
```bash
# Build development version with debugging tools
docker build -f Dockerfile.runpod --target development -t f5-tts-dev:latest .

# Run with volume mounts for development
docker run --gpus all -p 8000:8000 \
  -v $(pwd):/app \
  -e PYTHONUNBUFFERED=1 \
  f5-tts-dev:latest
```

### Local Development
```bash
# Set up Python environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install flash-attn --no-build-isolation

# Run handler locally
python runpod-handler.py
```

### Registry Operations
```bash
# Tag for registry
docker tag f5-tts-serverless:latest your-registry/f5-tts:latest

# Push to Docker Hub
docker push your-registry/f5-tts:latest

# Push to GitHub Container Registry
docker tag f5-tts-serverless:latest ghcr.io/username/f5-tts:latest
docker push ghcr.io/username/f5-tts:latest
```

## Testing

### Local Testing
```bash
# Test container locally
docker run --gpus all -p 8000:8000 \
  -e S3_BUCKET=test-bucket \
  -e AWS_ACCESS_KEY_ID=test-key \
  -e AWS_SECRET_ACCESS_KEY=test-secret \
  f5-tts-serverless:latest

# Test API endpoint
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"input": {"text": "Hello world test"}}'
```

### Model Validation
```bash
# Validate F5-TTS model loading
docker run --gpus all f5-tts-serverless:latest python -c "
from f5_tts.api import F5TTS
model = F5TTS(model_type='F5-TTS')
print('Model loaded successfully')
"

# Test flash attention
docker run --gpus all f5-tts-serverless:latest python -c "
import flash_attn
print(f'Flash Attention version: {flash_attn.__version__}')
"
```

## CI/CD Pipeline

### GitHub Actions (Automated)
The repository includes automated builds via GitHub Actions:

```yaml
# .github/workflows/docker-build.yml
name: Build and Push Docker Image
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -f Dockerfile.runpod -t f5-tts-test .
      - name: Push to Docker Hub
        if: github.ref == 'refs/heads/main'
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker tag f5-tts-test ${{ secrets.DOCKER_USERNAME }}/f5-tts:latest
          docker push ${{ secrets.DOCKER_USERNAME }}/f5-tts:latest
```

### Manual Deployment to RunPod

1. **Build and Push Container**:
   ```bash
   docker build -f Dockerfile.runpod -t your-registry/f5-tts:latest .
   docker push your-registry/f5-tts:latest
   ```

2. **Create RunPod Endpoint**:
   - Go to RunPod Serverless console
   - Create new endpoint
   - Set image: `your-registry/f5-tts:latest`
   - Configure environment variables
   - Set GPU type (A40 or better recommended)

3. **Test Deployment**:
   ```bash
   curl -X POST "https://api.runpod.ai/v2/{endpoint-id}/runsync" \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"input": {"text": "Deployment test successful"}}'
   ```

## Performance Optimization

### Build Optimizations
- **Multi-stage builds**: Separate build dependencies from runtime
- **Layer caching**: Optimize Dockerfile for better layer reuse
- **Model pre-loading**: Download models during build time
- **Flash attention**: Pre-compiled for CUDA compatibility

### Runtime Optimizations
- **Model caching**: Keep models in memory between requests
- **Batch processing**: Process multiple requests efficiently
- **GPU utilization**: Optimize CUDA memory usage
- **Storage management**: Efficient temporary file cleanup

## Troubleshooting

### Build Issues

**Issue: CUDA compatibility errors**
```
ERROR: Could not find a version that satisfies the requirement flash-attn
```
**Solution**: Verify CUDA version compatibility and use pre-built wheels:
```bash
# Check CUDA version
nvidia-smi

# Install compatible flash-attn
pip install flash-attn --no-build-isolation --extra-index-url https://download.pytorch.org/whl/cu118
```

**Issue: Out of disk space during build**
```
ERROR: No space left on device
```
**Solution**: Clean Docker cache and increase build space:
```bash
docker system prune -a
docker buildx prune
```

**Issue: Model download failures**
```
ERROR: Failed to download F5-TTS models
```
**Solution**: Check network connectivity and add retry logic:
```bash
# Test model download
python -c "from f5_tts.api import F5TTS; F5TTS(model_type='F5-TTS')"
```

### Runtime Issues

**Issue: GPU memory errors**
```
RuntimeError: CUDA out of memory
```
**Solution**: Use GPU with more VRAM or optimize batch size:
```bash
# Check GPU memory
nvidia-smi

# Use A40 or A100 on RunPod
```

**Issue: S3 connection failures**
```
ERROR: Unable to connect to S3 bucket
```
**Solution**: Verify S3 credentials and bucket permissions:
```bash
# Test S3 access
aws s3 ls s3://your-bucket-name/
```

### Performance Issues

**Issue: Slow cold starts (>10 seconds)**
- Verify models are pre-loaded in container
- Check for runtime model downloads
- Optimize Dockerfile layer caching

**Issue: High memory usage**
- Monitor GPU memory usage
- Implement model memory cleanup
- Use appropriate GPU instance types

## Keywords <!-- #keywords -->
build, deployment, Docker, RunPod, serverless, F5-TTS, CUDA, flash-attn, CI/CD, testing, troubleshooting, performance, optimization