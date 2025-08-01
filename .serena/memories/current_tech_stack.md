# F5-TTS RunPod Tech Stack

## Core Technologies
- **Python 3.x**: Main programming language
- **F5-TTS**: Official F5-TTS text-to-speech model (from ghcr.io/swivid/f5-tts:main)
- **PyTorch**: Deep learning framework for F5-TTS models
- **RunPod**: Serverless GPU infrastructure platform
- **Docker**: Containerization for consistent deployment

## Key Dependencies
- **runpod**: RunPod serverless SDK for job handling
- **boto3**: AWS S3 client for file storage (supports S3-compatible services)
- **torch/torchaudio**: PyTorch ecosystem for audio processing
- **librosa**: Audio analysis and processing
- **soundfile**: Audio file I/O
- **pydantic**: Data validation and serialization
- **requests**: HTTP client for downloading files

## Storage & Infrastructure
- **S3-Compatible Storage**: AWS S3, Backblaze B2, DigitalOcean Spaces
- **RunPod GPU Infrastructure**: CUDA-enabled containers
- **Docker Hub**: Container registry (gemneye/f5-tts-runpod-serverless)

## Build System
- **Docker**: Multi-stage builds using official F5-TTS base image
- **GitHub Actions**: Automated CI/CD pipeline for container builds