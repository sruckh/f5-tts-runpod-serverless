"""
Configuration constants for F5-TTS RunPod Serverless

Defines paths, URLs, and constants for the 2-layer architecture.
"""

import os
from pathlib import Path

# Network Volume Configuration
NETWORK_VOLUME_PATH = Path("/runpod-volume/f5tts")
VENV_PATH = NETWORK_VOLUME_PATH / "venv"
MODELS_PATH = NETWORK_VOLUME_PATH / "models"
TEMP_PATH = NETWORK_VOLUME_PATH / "temp"
LOGS_PATH = NETWORK_VOLUME_PATH / "logs"
CACHE_PATH = NETWORK_VOLUME_PATH / "cache"
SETUP_COMPLETE_FLAG = NETWORK_VOLUME_PATH / "setup_complete.flag"

# Model Paths
F5TTS_MODELS_PATH = MODELS_PATH / "f5-tts"
WHISPERX_MODELS_PATH = MODELS_PATH / "whisperx"

# PyTorch Installation
PYTORCH_INDEX_URL = "https://download.pytorch.org/whl/cu126"
PYTORCH_VERSION = "torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0"

# Flash Attention Wheel for Python 3.10 + CUDA 12.6 + PyTorch 2.6
FLASH_ATTN_WHEEL = (
    "https://github.com/Dao-AILab/flash-attention/releases/download/"
    "v2.8.0.post2/flash_attn-2.8.0.post2+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl"
)

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")

# Performance Settings
DEFAULT_BATCH_SIZE = 16
DEFAULT_COMPUTE_TYPE = "float16"
WHISPERX_MODEL = "large-v2"

# Timeouts and Retries
SETUP_TIMEOUT = 1800  # 30 minutes for first-time setup
MODEL_LOAD_TIMEOUT = 600  # 10 minutes for model loading
S3_RETRY_COUNT = 3
S3_RETRY_DELAY = 2

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Runtime Requirements (installed on network volume)
RUNTIME_REQUIREMENTS = [
    f"{PYTORCH_VERSION} --index-url {PYTORCH_INDEX_URL}",
    f"{FLASH_ATTN_WHEEL}",
    "whisperx",
    "git+https://github.com/SWivid/F5-TTS.git",
    "python-ass>=0.5.0",
    "librosa>=0.10.0",
    "soundfile>=0.12.0",
    "torchaudio>=2.6.0",
    "transformers>=4.40.0",
    "accelerate>=0.30.0",
    "datasets>=2.20.0",
    "nltk>=3.8.1",
    "pyannote-audio>=3.1.0",
    "faster-whisper>=1.0.0"
]
Configuration constants for F5-TTS RunPod Serverless

Defines paths, URLs, and constants for the 2-layer architecture.
"""

import os
from pathlib import Path

# Network Volume Configuration
NETWORK_VOLUME_PATH = Path("/runpod-volume/f5tts")
VENV_PATH = NETWORK_VOLUME_PATH / "venv"
MODELS_PATH = NETWORK_VOLUME_PATH / "models"
TEMP_PATH = NETWORK_VOLUME_PATH / "temp"
LOGS_PATH = NETWORK_VOLUME_PATH / "logs"
CACHE_PATH = NETWORK_VOLUME_PATH / "cache"
SETUP_COMPLETE_FLAG = NETWORK_VOLUME_PATH / "setup_complete.flag"

# Model Paths
F5TTS_MODELS_PATH = MODELS_PATH / "f5-tts"
WHISPERX_MODELS_PATH = MODELS_PATH / "whisperx"

# PyTorch Installation
PYTORCH_INDEX_URL = "https://download.pytorch.org/whl/cu126"
PYTORCH_VERSION = "torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0"

# Flash Attention Wheel for Python 3.10 + CUDA 12.6 + PyTorch 2.6
FLASH_ATTN_WHEEL = (
    "https://github.com/Dao-AILab/flash-attention/releases/download/"
    "v2.8.0.post2/flash_attn-2.8.0.post2+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl"
)

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL")

# Performance Settings
DEFAULT_BATCH_SIZE = 16
DEFAULT_COMPUTE_TYPE = "float16"
WHISPERX_MODEL = "large-v2"

# Timeouts and Retries
SETUP_TIMEOUT = 1800  # 30 minutes for first-time setup
MODEL_LOAD_TIMEOUT = 600  # 10 minutes for model loading
S3_RETRY_COUNT = 3
S3_RETRY_DELAY = 2

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Runtime Requirements (installed on network volume)
RUNTIME_REQUIREMENTS = [
    f"{PYTORCH_VERSION} --index-url {PYTORCH_INDEX_URL}",
    f"{FLASH_ATTN_WHEEL}",
    "whisperx",
    "git+https://github.com/SWivid/F5-TTS.git",
    "python-ass>=0.5.0",
    "librosa>=0.10.0",
    "soundfile>=0.12.0",
    "torchaudio>=2.6.0",
    "transformers>=4.40.0",
    "accelerate>=0.30.0",
    "datasets>=2.20.0",
    "nltk>=3.8.1",
    "pyannote-audio>=3.1.0",
    "faster-whisper>=1.0.0"
]