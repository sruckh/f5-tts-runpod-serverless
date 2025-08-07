# F5-TTS RunPod Serverless - Deployment & Usage Guide

## 🚀 Complete Deployment Guide

### Overview

This guide covers the complete deployment and usage of the F5-TTS RunPod Serverless system with 2-layer architecture optimized for:
- **Slim container builds** (<2GB) for GitHub Actions
- **Fast inference** (1-3s) with warm loading
- **Professional subtitles** with word-level timing
- **S3 integration** for seamless audio processing

## 📋 Pre-Deployment Requirements

### 1. GitHub Repository Setup
```bash
# Clone or fork this repository
git clone https://github.com/your-username/f5-tts-runpod
cd f5-tts-runpod

# Ensure all files are present (run validation)
python CONTRIBUTING.md  # Our test suite
```

### 2. Docker Hub Account
- Create account at https://hub.docker.com
- Create repository: `your-username/f5-tts-runpod`
- Generate access token for GitHub Actions

### 3. GitHub Actions Secrets
Add these secrets to your repository (`Settings > Secrets > Actions`):
```
DOCKER_HUB_USERNAME: your-dockerhub-username
DOCKER_HUB_ACCESS_TOKEN: your-access-token
```

### 4. S3 Bucket Setup
```bash
# Create S3 bucket with proper structure
aws s3 mb s3://your-f5tts-bucket
aws s3api put-bucket-versioning --bucket your-f5tts-bucket --versioning-configuration Status=Enabled
```

## 🏗️ Build & Deployment Process

### Step 1: GitHub Actions Build
The repository includes automated GitHub Actions workflow:

```yaml
# .github/workflows/docker-build.yml automatically:
# 1. Builds slim container (<2GB)
# 2. Pushes to Docker Hub
# 3. Tags with git commit SHA
# 4. Creates latest tag
```

**Trigger build:**
```bash
git add .
git commit -m "Deploy F5-TTS RunPod serverless v3.0"
git push origin main
```

Monitor build at: `https://github.com/your-username/f5-tts-runpod/actions`

### Step 2: RunPod Template Setup

#### A. Create Template
1. Go to https://runpod.io/console/serverless
2. Click "New Template"
3. Configure:
   ```
   Template Name: f5-tts-v3
   Container Image: your-username/f5-tts-runpod:latest
   Container Disk: 5 GB
   Ports: 8000 (HTTP)
   ```

#### B. Environment Variables
```bash
RUNPOD_WEBHOOK_SECRET=your-webhook-secret
S3_BUCKET_NAME=your-f5tts-bucket
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1
HF_TOKEN=your-huggingface-token  # Optional for private models
```

#### C. Advanced Settings
```bash
Container Start Command: python handler.py
HTTP Port: 8000
Request Timeout: 300 (5 minutes)
```

### Step 3: Endpoint Deployment
1. Click "Deploy" on your template
2. Select:
   ```
   GPUs: 1x RTX 4090 (recommended)
   Workers: Min 0, Max 3
   Idle Timeout: 5 seconds
   Flashboot: Enabled
   ```

3. Note your endpoint URL: `https://api.runpod.ai/v2/[endpoint-id]/run`

## 📡 API Usage Guide

### Request Format
```bash
curl -X POST https://api.runpod.ai/v2/[endpoint-id]/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [your-runpod-api-key]" \
  -d '{
    "input": {
      "input_audio_s3": "s3://your-bucket/input/speaker-sample.wav",
      "target_text": "Hello world, this is F5-TTS generating speech with perfect timing.",
      "speaker_audio_s3": "s3://your-bucket/speakers/voice-clone-source.wav",
      "subtitle_type": "sentence",
      "video_width": 1920,
      "video_height": 1080,
      "add_karaoke": true
    }
  }'
```

### Response Format
```json
{
  "id": "unique-job-id",
  "status": "COMPLETED",
  "output": {
    "generated_audio_s3": "s3://your-bucket/output/generated-speech.wav",
    "subtitle_file_s3": "s3://your-bucket/output/subtitles.ass",
    "word_timings": [
      {"word": "Hello", "start": 0.0, "end": 0.5},
      {"word": "world", "start": 0.5, "end": 1.0}
    ],
    "processing_time": 2.3,
    "audio_duration": 5.2,
    "subtitle_events": 12
  }
}
```

## 🔧 Configuration Options

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `input_audio_s3` | string | Yes | S3 URL to reference audio for cloning |
| `target_text` | string | Yes | Text to synthesize into speech |
| `speaker_audio_s3` | string | Yes | S3 URL to speaker voice sample |
| `subtitle_type` | string | No | 'word' or 'sentence' (default: 'sentence') |
| `video_width` | integer | No | Subtitle resolution width (default: 1920) |
| `video_height` | integer | No | Subtitle resolution height (default: 1080) |
| `add_karaoke` | boolean | No | Add karaoke effects (default: false) |
| `max_duration` | float | No | Max subtitle duration in seconds (default: 5.0) |
| `max_words_per_line` | integer | No | Max words per subtitle (default: 8) |

### S3 URL Formats
Both formats are supported:
- `s3://bucket-name/path/to/file.wav`
- `https://bucket-name.s3.amazonaws.com/path/to/file.wav`

### Audio Requirements
- **Input formats**: WAV, MP3, M4A, FLAC
- **Sample rate**: 16kHz-48kHz (auto-converted)
- **Duration**: 5-30 seconds for speaker samples
- **Quality**: Higher quality = better voice cloning

## ⚡ Performance Optimization

### Cold Start vs Warm Start
- **Cold start**: ~25-30s (first request or after idle)
- **Warm start**: ~1-3s (subsequent requests)
- **Network volume setup**: One-time per worker lifecycle

### Scaling Strategy
```python
# Recommended configuration
Workers:
  Min: 0  # Cost optimization
  Max: 3  # Performance scaling
  
Idle Timeout: 5s  # Quick scale-down
Flashboot: Enabled  # Faster cold starts
```

### Resource Usage
- **GPU Memory**: ~4-6GB (RTX 4090 recommended)
- **System Memory**: ~8GB during processing
- **Storage**: 15GB network volume + 5GB container
- **Network**: ~50MB/request (model downloads)

## 🔍 Monitoring & Debugging

### Request Logs
```bash
# View logs in RunPod console
curl -X GET https://api.runpod.ai/v2/[endpoint-id]/requests/[request-id] \
  -H "Authorization: Bearer [your-api-key]"
```

### Common Issues & Solutions

#### Issue 1: Cold Start Timeout
```
Error: Request timeout during environment setup
Solution: Increase request timeout to 300s
```

#### Issue 2: S3 Access Denied
```
Error: NoCredentialsError or AccessDenied
Solution: Verify AWS credentials and bucket permissions
```

#### Issue 3: Model Loading Failure
```
Error: Model download failed
Solution: Check HF_TOKEN and network connectivity
```

#### Issue 4: Audio Format Errors
```
Error: Unsupported audio format
Solution: Convert to WAV 16kHz mono format
```

### Health Check Endpoint
```bash
curl https://api.runpod.ai/v2/[endpoint-id]/health
```

### Performance Metrics
Monitor in RunPod dashboard:
- Request latency percentiles
- Error rates by type
- GPU utilization
- Cost per request

## 💰 Cost Optimization

### Pricing Calculator
```python
# RTX 4090 pricing example
Base rate: $0.50/hour
Cold start: 30s = $0.0042
Warm request: 2s = $0.0003

# 100 requests/day scenario:
# 1 cold start + 99 warm = $0.03/day
# Monthly: ~$1.00
```

### Optimization Tips
1. **Batch requests** when possible
2. **Use idle timeout** of 5s for cost balance
3. **Monitor usage** in RunPod dashboard  
4. **Scale down** to 0 workers during low usage

## 🧪 Testing & Validation

### Local Testing
```bash
# Run validation suite
python CONTRIBUTING.md

# Test individual components
python -c "from s3_utils import S3Client; print('S3 client OK')"
python -c "from TASKS import ASSSubtitleGenerator; print('Subtitle generator OK')"
```

### End-to-End Testing
```bash
# Test with sample data
curl -X POST https://api.runpod.ai/v2/[endpoint-id]/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [your-api-key]" \
  -d @test_request.json
```

### Performance Benchmarking
```python
import time
import requests

def benchmark_endpoint(endpoint_url, num_requests=10):
    times = []
    for i in range(num_requests):
        start = time.time()
        response = requests.post(endpoint_url, json=test_payload)
        end = time.time()
        times.append(end - start)
    
    print(f"Average: {sum(times)/len(times):.2f}s")
    print(f"P95: {sorted(times)[int(0.95*len(times))]:.2f}s")
```

## 🔄 Updates & Maintenance

### Version Updates
```bash
# Update version in README.md
# Commit and push to trigger new build
git tag v3.1.0
git push origin v3.1.0
```

### Dependency Updates
```bash
# Update requirements files
# Test locally before deploying
python CONTRIBUTING.md  # Run tests
```

### Model Updates
Models are loaded from network volume and cached:
- **F5-TTS models**: Auto-downloaded from HuggingFace
- **WhisperX models**: Cached on first use
- **Clear cache**: Restart endpoint to refresh models

## 📞 Support & Troubleshooting

### Getting Help
1. **Check logs** in RunPod console first
2. **Run validation** suite locally
3. **Review architecture** docs for design decisions
4. **Test S3 permissions** independently

### Common Troubleshooting Commands
```bash
# Test S3 connectivity
aws s3 ls s3://your-bucket/

# Validate audio files
ffprobe your-audio-file.wav

# Check Docker image
docker pull your-username/f5-tts-runpod:latest
docker run -it --rm your-username/f5-tts-runpod:latest /bin/bash
```

### Debug Mode
Enable detailed logging by adding environment variable:
```bash
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

## 🎯 Production Deployment Checklist

Before production deployment:

- [ ] **Architecture validated**: 2-layer design implemented
- [ ] **Container size**: <2GB build confirmed  
- [ ] **Performance tested**: <3s warm inference verified
- [ ] **S3 integration**: Upload/download working
- [ ] **Subtitle generation**: ASS format validated
- [ ] **Error handling**: Comprehensive error responses
- [ ] **Monitoring**: Logging and metrics configured
- [ ] **Security**: API keys and permissions secured
- [ ] **Cost analysis**: Usage patterns estimated
- [ ] **Documentation**: All guides updated

## 🌟 Advanced Features

### Custom Subtitle Styles
```python
# Modify TASKS.md (ASSSubtitleGenerator) for custom styles
custom_styles = [
    {
        'Name': 'Corporate',
        'Fontname': 'Helvetica',
        'Fontsize': 20,
        'PrimaryColour': '&H0080FF',  # Orange
        'Alignment': 8  # Top center
    }
]
```

### Batch Processing
```bash
# Process multiple files
for file in input/*.wav; do
  curl -X POST [endpoint] -d "{\"input_audio_s3\": \"s3://bucket/$file\", ...}"
done
```

### Integration Examples
- **Video editing**: Use ASS subtitles with FFmpeg
- **Content creation**: Automated voice generation
- **Accessibility**: Auto-subtitle generation
- **Localization**: Multi-language speech synthesis

---

## 📝 Summary

This F5-TTS RunPod Serverless system provides:

✅ **Fast deployment** with automated GitHub Actions  
✅ **Cost-effective** scaling with warm loading  
✅ **Professional quality** subtitles with timing  
✅ **S3 integration** for seamless workflows  
✅ **Production-ready** error handling and monitoring  

Ready for professional video production, content creation, and accessibility applications.# F5-TTS RunPod Serverless - Deployment & Usage Guide

## 🚀 Complete Deployment Guide

### Overview

This guide covers the complete deployment and usage of the F5-TTS RunPod Serverless system with 2-layer architecture optimized for:
- **Slim container builds** (<2GB) for GitHub Actions
- **Fast inference** (1-3s) with warm loading
- **Professional subtitles** with word-level timing
- **S3 integration** for seamless audio processing

## 📋 Pre-Deployment Requirements

### 1. GitHub Repository Setup
```bash
# Clone or fork this repository
git clone https://github.com/your-username/f5-tts-runpod
cd f5-tts-runpod

# Ensure all files are present (run validation)
python CONTRIBUTING.md  # Our test suite
```

### 2. Docker Hub Account
- Create account at https://hub.docker.com
- Create repository: `your-username/f5-tts-runpod`
- Generate access token for GitHub Actions

### 3. GitHub Actions Secrets
Add these secrets to your repository (`Settings > Secrets > Actions`):
```
DOCKER_HUB_USERNAME: your-dockerhub-username
DOCKER_HUB_ACCESS_TOKEN: your-access-token
```

### 4. S3 Bucket Setup
```bash
# Create S3 bucket with proper structure
aws s3 mb s3://your-f5tts-bucket
aws s3api put-bucket-versioning --bucket your-f5tts-bucket --versioning-configuration Status=Enabled
```

## 🏗️ Build & Deployment Process

### Step 1: GitHub Actions Build
The repository includes automated GitHub Actions workflow:

```yaml
# .github/workflows/docker-build.yml automatically:
# 1. Builds slim container (<2GB)
# 2. Pushes to Docker Hub
# 3. Tags with git commit SHA
# 4. Creates latest tag
```

**Trigger build:**
```bash
git add .
git commit -m "Deploy F5-TTS RunPod serverless v3.0"
git push origin main
```

Monitor build at: `https://github.com/your-username/f5-tts-runpod/actions`

### Step 2: RunPod Template Setup

#### A. Create Template
1. Go to https://runpod.io/console/serverless
2. Click "New Template"
3. Configure:
   ```
   Template Name: f5-tts-v3
   Container Image: your-username/f5-tts-runpod:latest
   Container Disk: 5 GB
   Ports: 8000 (HTTP)
   ```

#### B. Environment Variables
```bash
RUNPOD_WEBHOOK_SECRET=your-webhook-secret
S3_BUCKET_NAME=your-f5tts-bucket
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1
HF_TOKEN=your-huggingface-token  # Optional for private models
```

#### C. Advanced Settings
```bash
Container Start Command: python handler.py
HTTP Port: 8000
Request Timeout: 300 (5 minutes)
```

### Step 3: Endpoint Deployment
1. Click "Deploy" on your template
2. Select:
   ```
   GPUs: 1x RTX 4090 (recommended)
   Workers: Min 0, Max 3
   Idle Timeout: 5 seconds
   Flashboot: Enabled
   ```

3. Note your endpoint URL: `https://api.runpod.ai/v2/[endpoint-id]/run`

## 📡 API Usage Guide

### Request Format
```bash
curl -X POST https://api.runpod.ai/v2/[endpoint-id]/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [your-runpod-api-key]" \
  -d '{
    "input": {
      "input_audio_s3": "s3://your-bucket/input/speaker-sample.wav",
      "target_text": "Hello world, this is F5-TTS generating speech with perfect timing.",
      "speaker_audio_s3": "s3://your-bucket/speakers/voice-clone-source.wav",
      "subtitle_type": "sentence",
      "video_width": 1920,
      "video_height": 1080,
      "add_karaoke": true
    }
  }'
```

### Response Format
```json
{
  "id": "unique-job-id",
  "status": "COMPLETED",
  "output": {
    "generated_audio_s3": "s3://your-bucket/output/generated-speech.wav",
    "subtitle_file_s3": "s3://your-bucket/output/subtitles.ass",
    "word_timings": [
      {"word": "Hello", "start": 0.0, "end": 0.5},
      {"word": "world", "start": 0.5, "end": 1.0}
    ],
    "processing_time": 2.3,
    "audio_duration": 5.2,
    "subtitle_events": 12
  }
}
```

## 🔧 Configuration Options

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `input_audio_s3` | string | Yes | S3 URL to reference audio for cloning |
| `target_text` | string | Yes | Text to synthesize into speech |
| `speaker_audio_s3` | string | Yes | S3 URL to speaker voice sample |
| `subtitle_type` | string | No | 'word' or 'sentence' (default: 'sentence') |
| `video_width` | integer | No | Subtitle resolution width (default: 1920) |
| `video_height` | integer | No | Subtitle resolution height (default: 1080) |
| `add_karaoke` | boolean | No | Add karaoke effects (default: false) |
| `max_duration` | float | No | Max subtitle duration in seconds (default: 5.0) |
| `max_words_per_line` | integer | No | Max words per subtitle (default: 8) |

### S3 URL Formats
Both formats are supported:
- `s3://bucket-name/path/to/file.wav`
- `https://bucket-name.s3.amazonaws.com/path/to/file.wav`

### Audio Requirements
- **Input formats**: WAV, MP3, M4A, FLAC
- **Sample rate**: 16kHz-48kHz (auto-converted)
- **Duration**: 5-30 seconds for speaker samples
- **Quality**: Higher quality = better voice cloning

## ⚡ Performance Optimization

### Cold Start vs Warm Start
- **Cold start**: ~25-30s (first request or after idle)
- **Warm start**: ~1-3s (subsequent requests)
- **Network volume setup**: One-time per worker lifecycle

### Scaling Strategy
```python
# Recommended configuration
Workers:
  Min: 0  # Cost optimization
  Max: 3  # Performance scaling
  
Idle Timeout: 5s  # Quick scale-down
Flashboot: Enabled  # Faster cold starts
```

### Resource Usage
- **GPU Memory**: ~4-6GB (RTX 4090 recommended)
- **System Memory**: ~8GB during processing
- **Storage**: 15GB network volume + 5GB container
- **Network**: ~50MB/request (model downloads)

## 🔍 Monitoring & Debugging

### Request Logs
```bash
# View logs in RunPod console
curl -X GET https://api.runpod.ai/v2/[endpoint-id]/requests/[request-id] \
  -H "Authorization: Bearer [your-api-key]"
```

### Common Issues & Solutions

#### Issue 1: Cold Start Timeout
```
Error: Request timeout during environment setup
Solution: Increase request timeout to 300s
```

#### Issue 2: S3 Access Denied
```
Error: NoCredentialsError or AccessDenied
Solution: Verify AWS credentials and bucket permissions
```

#### Issue 3: Model Loading Failure
```
Error: Model download failed
Solution: Check HF_TOKEN and network connectivity
```

#### Issue 4: Audio Format Errors
```
Error: Unsupported audio format
Solution: Convert to WAV 16kHz mono format
```

### Health Check Endpoint
```bash
curl https://api.runpod.ai/v2/[endpoint-id]/health
```

### Performance Metrics
Monitor in RunPod dashboard:
- Request latency percentiles
- Error rates by type
- GPU utilization
- Cost per request

## 💰 Cost Optimization

### Pricing Calculator
```python
# RTX 4090 pricing example
Base rate: $0.50/hour
Cold start: 30s = $0.0042
Warm request: 2s = $0.0003

# 100 requests/day scenario:
# 1 cold start + 99 warm = $0.03/day
# Monthly: ~$1.00
```

### Optimization Tips
1. **Batch requests** when possible
2. **Use idle timeout** of 5s for cost balance
3. **Monitor usage** in RunPod dashboard  
4. **Scale down** to 0 workers during low usage

## 🧪 Testing & Validation

### Local Testing
```bash
# Run validation suite
python CONTRIBUTING.md

# Test individual components
python -c "from s3_utils import S3Client; print('S3 client OK')"
python -c "from TASKS import ASSSubtitleGenerator; print('Subtitle generator OK')"
```

### End-to-End Testing
```bash
# Test with sample data
curl -X POST https://api.runpod.ai/v2/[endpoint-id]/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [your-api-key]" \
  -d @test_request.json
```

### Performance Benchmarking
```python
import time
import requests

def benchmark_endpoint(endpoint_url, num_requests=10):
    times = []
    for i in range(num_requests):
        start = time.time()
        response = requests.post(endpoint_url, json=test_payload)
        end = time.time()
        times.append(end - start)
    
    print(f"Average: {sum(times)/len(times):.2f}s")
    print(f"P95: {sorted(times)[int(0.95*len(times))]:.2f}s")
```

## 🔄 Updates & Maintenance

### Version Updates
```bash
# Update version in README.md
# Commit and push to trigger new build
git tag v3.1.0
git push origin v3.1.0
```

### Dependency Updates
```bash
# Update requirements files
# Test locally before deploying
python CONTRIBUTING.md  # Run tests
```

### Model Updates
Models are loaded from network volume and cached:
- **F5-TTS models**: Auto-downloaded from HuggingFace
- **WhisperX models**: Cached on first use
- **Clear cache**: Restart endpoint to refresh models

## 📞 Support & Troubleshooting

### Getting Help
1. **Check logs** in RunPod console first
2. **Run validation** suite locally
3. **Review architecture** docs for design decisions
4. **Test S3 permissions** independently

### Common Troubleshooting Commands
```bash
# Test S3 connectivity
aws s3 ls s3://your-bucket/

# Validate audio files
ffprobe your-audio-file.wav

# Check Docker image
docker pull your-username/f5-tts-runpod:latest
docker run -it --rm your-username/f5-tts-runpod:latest /bin/bash
```

### Debug Mode
Enable detailed logging by adding environment variable:
```bash
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

## 🎯 Production Deployment Checklist

Before production deployment:

- [ ] **Architecture validated**: 2-layer design implemented
- [ ] **Container size**: <2GB build confirmed  
- [ ] **Performance tested**: <3s warm inference verified
- [ ] **S3 integration**: Upload/download working
- [ ] **Subtitle generation**: ASS format validated
- [ ] **Error handling**: Comprehensive error responses
- [ ] **Monitoring**: Logging and metrics configured
- [ ] **Security**: API keys and permissions secured
- [ ] **Cost analysis**: Usage patterns estimated
- [ ] **Documentation**: All guides updated

## 🌟 Advanced Features

### Custom Subtitle Styles
```python
# Modify TASKS.md (ASSSubtitleGenerator) for custom styles
custom_styles = [
    {
        'Name': 'Corporate',
        'Fontname': 'Helvetica',
        'Fontsize': 20,
        'PrimaryColour': '&H0080FF',  # Orange
        'Alignment': 8  # Top center
    }
]
```

### Batch Processing
```bash
# Process multiple files
for file in input/*.wav; do
  curl -X POST [endpoint] -d "{\"input_audio_s3\": \"s3://bucket/$file\", ...}"
done
```

### Integration Examples
- **Video editing**: Use ASS subtitles with FFmpeg
- **Content creation**: Automated voice generation
- **Accessibility**: Auto-subtitle generation
- **Localization**: Multi-language speech synthesis

---

## 📝 Summary

This F5-TTS RunPod Serverless system provides:

✅ **Fast deployment** with automated GitHub Actions  
✅ **Cost-effective** scaling with warm loading  
✅ **Professional quality** subtitles with timing  
✅ **S3 integration** for seamless workflows  
✅ **Production-ready** error handling and monitoring  

Ready for professional video production, content creation, and accessibility applications.