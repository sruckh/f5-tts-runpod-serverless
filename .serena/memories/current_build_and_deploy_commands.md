# F5-TTS RunPod Build & Deploy Commands

## Docker Build Commands
```bash
# Build the RunPod serverless container
docker build -f Dockerfile.runpod -t f5-tts-runpod:latest .

# Build with specific tag for Docker Hub
docker build -f Dockerfile.runpod -t gemneye/f5-tts-runpod-serverless:latest .

# Push to Docker Hub
docker push gemneye/f5-tts-runpod-serverless:latest
```

## Local Testing
```bash
# Run container locally for testing
docker run --gpus all -p 7860:7860 \
  -e S3_BUCKET=your-bucket \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  f5-tts-runpod:latest

# Test with environment file
docker run --gpus all -p 7860:7860 --env-file .env f5-tts-runpod:latest
```

## RunPod Deployment
```bash
# Deploy to RunPod using their web interface or API
# Image: gemneye/f5-tts-runpod-serverless:latest
# Port: 7860
# GPU: A100, RTX 4090, or similar CUDA-capable GPU
```

## Environment Variables (Required)
```bash
S3_BUCKET=your-s3-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
AWS_ENDPOINT_URL=https://s3.backblazeb2.com  # For Backblaze B2
ENABLE_S3_MODEL_CACHE=true
```

## No Linting/Testing Commands
- This project currently has no formal linting or test suite
- Code quality managed through manual review and runtime testing
- Consider adding: black, flake8, pytest for future development