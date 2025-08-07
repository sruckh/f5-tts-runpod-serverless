# F5-TTS RunPod Serverless - Runtime Dependencies (HEAVY ML)
#
# These dependencies are installed at runtime on the network volume.
# They are NOT included in the container to keep it under 2GB.

# PyTorch with CUDA 12.6 support (installed via index URL)
# torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu126

# Flash Attention (specific wheel for Python 3.10 + CUDA 12.6 + PyTorch 2.6)
# https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.0.post2/flash_attn-2.8.0.post2+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl

# F5-TTS (latest from GitHub)
git+https://github.com/SWivid/F5-TTS.git

# WhisperX for word-level timing
whisperx>=3.1.0

# Audio processing
librosa>=0.10.0
soundfile>=0.12.0
torchaudio>=2.6.0

# Transformers and ML frameworks
transformers>=4.40.0
accelerate>=0.30.0
datasets>=2.20.0

# Natural language processing
nltk>=3.8.1

# Speaker diarization  
pyannote-audio>=3.1.0

# Faster whisper backend
faster-whisper>=1.0.0

# Subtitle generation
python-ass>=0.5.0

# Additional audio processing
ffmpeg-python>=0.2.0
scipy>=1.11.0
numpy>=1.24.0

# Model utilities
huggingface-hub>=0.20.0
safetensors>=0.4.0

# Performance and memory optimization
einops>=0.7.0
cached-path>=1.6.0# F5-TTS RunPod Serverless - Runtime Dependencies (HEAVY ML)
#
# These dependencies are installed at runtime on the network volume.
# They are NOT included in the container to keep it under 2GB.

# PyTorch with CUDA 12.6 support (installed via index URL)
# torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu126

# Flash Attention (specific wheel for Python 3.10 + CUDA 12.6 + PyTorch 2.6)
# https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.0.post2/flash_attn-2.8.0.post2+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl

# F5-TTS (latest from GitHub)
git+https://github.com/SWivid/F5-TTS.git

# WhisperX for word-level timing
whisperx>=3.1.0

# Audio processing
librosa>=0.10.0
soundfile>=0.12.0
torchaudio>=2.6.0

# Transformers and ML frameworks
transformers>=4.40.0
accelerate>=0.30.0
datasets>=2.20.0

# Natural language processing
nltk>=3.8.1

# Speaker diarization  
pyannote-audio>=3.1.0

# Faster whisper backend
faster-whisper>=1.0.0

# Subtitle generation
python-ass>=0.5.0

# Additional audio processing
ffmpeg-python>=0.2.0
scipy>=1.11.0
numpy>=1.24.0

# Model utilities
huggingface-hub>=0.20.0
safetensors>=0.4.0

# Performance and memory optimization
einops>=0.7.0
cached-path>=1.6.0