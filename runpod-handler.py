#!/usr/bin/env python3
"""
F5-TTS RunPod Serverless Handler - v3.0
2-Layer Architecture Implementation

Layer 1: This file (runs in slim container)
Layer 2: Heavy ML dependencies (installed on network volume at runtime)

Architecture:
- Cold start: Setup network volume environment and install dependencies
- Warm loading: Use cached models for 1-3s inference
- Error resilient: Comprehensive error handling and recovery
"""

import os
import sys
import json
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration constants
NETWORK_VOLUME_PATH = Path("/runpod-volume/f5tts")
VENV_PATH = NETWORK_VOLUME_PATH / "venv"
SETUP_COMPLETE_FLAG = NETWORK_VOLUME_PATH / "setup_complete.flag"

def check_setup_complete() -> bool:
    """Check if network volume setup is complete."""
    return SETUP_COMPLETE_FLAG.exists()

def setup_environment():
    """Setup network volume environment on first run."""
    try:
        logger.info("Setting up network volume environment...")
        
        # Create directory structure
        NETWORK_VOLUME_PATH.mkdir(parents=True, exist_ok=True)
        (NETWORK_VOLUME_PATH / "models").mkdir(exist_ok=True)
        (NETWORK_VOLUME_PATH / "temp").mkdir(exist_ok=True)
        (NETWORK_VOLUME_PATH / "logs").mkdir(exist_ok=True)
        (NETWORK_VOLUME_PATH / "cache").mkdir(exist_ok=True)
        
        logger.info("Created directory structure")
        
        # Import setup environment module
        from setup_environment import setup_network_volume_environment
        
        # Run the full setup
        setup_network_volume_environment()
        
        # Mark setup as complete
        SETUP_COMPLETE_FLAG.touch()
        logger.info("Environment setup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to setup environment: {e}")
        logger.error(traceback.format_exc())
        raise

def activate_virtual_environment():
    """Activate the virtual environment and update Python path."""
    try:
        # Add virtual environment to Python path
        venv_site_packages = VENV_PATH / "lib" / "python3.10" / "site-packages"
        if venv_site_packages.exists():
            sys.path.insert(0, str(venv_site_packages))
            logger.info(f"Activated virtual environment: {VENV_PATH}")
        else:
            raise RuntimeError(f"Virtual environment not found: {venv_site_packages}")
            
    except Exception as e:
        logger.error(f"Failed to activate virtual environment: {e}")
        raise

def load_models():
    """Load F5-TTS and WhisperX models for warm inference."""
    try:
        # Import heavy ML modules (only available after environment setup)
        from f5tts_engine import F5TTSEngine
        from whisperx_engine import WhisperXEngine
        
        # Initialize engines with model caching
        f5tts_engine = F5TTSEngine()
        whisperx_engine = WhisperXEngine()
        
        logger.info("Models loaded successfully for warm inference")
        return f5tts_engine, whisperx_engine
        
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        logger.error(traceback.format_exc())
        raise

def process_request(job_input: Dict[str, Any]) -> Dict[str, Any]:
    """Process F5-TTS request with word-level timing and subtitle generation."""
    try:
        # Extract input parameters
        text = job_input.get("text")
        audio_url = job_input.get("audio_url")
        voice_reference_url = job_input.get("voice_reference_url")
        options = job_input.get("options", {})
        
        if not text:
            raise ValueError("Missing required parameter: text")
        if not voice_reference_url:
            raise ValueError("Missing required parameter: voice_reference_url")
            
        logger.info(f"Processing F5-TTS request for text length: {len(text)}")
        
        # Import processing modules
        from f5tts_engine import process_tts
        from whisperx_engine import generate_word_timings
        from subtitle_generator import create_ass_subtitles
        from s3_client import upload_audio_to_s3, download_audio_from_s3
        
        # Download reference voice if needed
        reference_audio_path = None
        if voice_reference_url:
            reference_audio_path = download_audio_from_s3(voice_reference_url)
            logger.info("Downloaded reference voice audio")
        
        # Generate speech with F5-TTS
        output_audio_path = process_tts(
            text=text,
            reference_audio_path=reference_audio_path
        )
        logger.info("Generated speech with F5-TTS")
        
        # Generate word-level timings if requested
        word_timings = None
        subtitles_url = None
        
        if options.get("create_subtitles", False):
            word_timings = generate_word_timings(output_audio_path, text)
            logger.info("Generated word-level timings")
            
            # Create ASS subtitles if requested
            if options.get("subtitle_format") == "ass":
                subtitles_path = create_ass_subtitles(word_timings, text)
                subtitles_url = upload_audio_to_s3(subtitles_path, "subtitles")
                logger.info("Created ASS subtitles")
        
        # Upload output audio to S3
        output_audio_url = upload_audio_to_s3(output_audio_path, "output")
        logger.info("Uploaded output audio to S3")
        
        # Prepare response
        response = {
            "audio_url": output_audio_url,
            "processing_time": None,  # TODO: Add timing
            "text_length": len(text),
            "success": True
        }
        
        if word_timings:
            response["word_timings"] = word_timings
            
        if subtitles_url:
            response["subtitles_url"] = subtitles_url
            
        logger.info("Request processed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Failed to process request: {e}")
        logger.error(traceback.format_exc())
        return {
            "error": str(e),
            "success": False
        }

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main RunPod serverless handler.
    
    Implements 2-layer architecture:
    1. Cold start: Setup network volume environment
    2. Warm loading: Use cached models for fast inference
    """
    try:
        logger.info("F5-TTS RunPod Serverless Handler v3.0 starting...")
        
        job_input = job.get("input", {})
        job_id = job.get("id", "unknown")
        
        logger.info(f"Processing job {job_id}")
        
        # Check if environment setup is required (cold start)
        if not check_setup_complete():
            logger.info("Cold start detected - setting up environment...")
            setup_environment()
        else:
            logger.info("Warm start - using existing environment")
            
        # Activate virtual environment with ML dependencies
        activate_virtual_environment()
        
        # Process the request
        result = process_request(job_input)
        
        logger.info(f"Job {job_id} completed")
        return {"output": result}
        
    except Exception as e:
        error_msg = f"Handler failed: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        return {
            "error": error_msg,
            "traceback": traceback.format_exc()
        }

# RunPod serverless entry point
if __name__ == "__main__":
    try:
        import runpod
        logger.info("Starting RunPod serverless worker...")
        runpod.serverless.start({"handler": handler})
    except ImportError:
        logger.error("RunPod library not available - running in test mode")
        # Test mode for local development
        test_job = {
            "id": "test-123",
            "input": {
                "text": "Hello world, this is a test.",
                "voice_reference_url": "s3://test-bucket/reference.wav",
                "options": {
                    "create_subtitles": True,
                    "subtitle_format": "ass"
                }
            }
        }
        result = handler(test_job)
        print(json.dumps(result, indent=2))#!/usr/bin/env python3
"""
F5-TTS RunPod Serverless Handler - v3.0
2-Layer Architecture Implementation

Layer 1: This file (runs in slim container)
Layer 2: Heavy ML dependencies (installed on network volume at runtime)

Architecture:
- Cold start: Setup network volume environment and install dependencies
- Warm loading: Use cached models for 1-3s inference
- Error resilient: Comprehensive error handling and recovery
"""

import os
import sys
import json
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration constants
NETWORK_VOLUME_PATH = Path("/runpod-volume/f5tts")
VENV_PATH = NETWORK_VOLUME_PATH / "venv"
SETUP_COMPLETE_FLAG = NETWORK_VOLUME_PATH / "setup_complete.flag"

def check_setup_complete() -> bool:
    """Check if network volume setup is complete."""
    return SETUP_COMPLETE_FLAG.exists()

def setup_environment():
    """Setup network volume environment on first run."""
    try:
        logger.info("Setting up network volume environment...")
        
        # Create directory structure
        NETWORK_VOLUME_PATH.mkdir(parents=True, exist_ok=True)
        (NETWORK_VOLUME_PATH / "models").mkdir(exist_ok=True)
        (NETWORK_VOLUME_PATH / "temp").mkdir(exist_ok=True)
        (NETWORK_VOLUME_PATH / "logs").mkdir(exist_ok=True)
        (NETWORK_VOLUME_PATH / "cache").mkdir(exist_ok=True)
        
        logger.info("Created directory structure")
        
        # Import setup environment module
        from setup_environment import setup_network_volume_environment
        
        # Run the full setup
        setup_network_volume_environment()
        
        # Mark setup as complete
        SETUP_COMPLETE_FLAG.touch()
        logger.info("Environment setup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to setup environment: {e}")
        logger.error(traceback.format_exc())
        raise

def activate_virtual_environment():
    """Activate the virtual environment and update Python path."""
    try:
        # Add virtual environment to Python path
        venv_site_packages = VENV_PATH / "lib" / "python3.10" / "site-packages"
        if venv_site_packages.exists():
            sys.path.insert(0, str(venv_site_packages))
            logger.info(f"Activated virtual environment: {VENV_PATH}")
        else:
            raise RuntimeError(f"Virtual environment not found: {venv_site_packages}")
            
    except Exception as e:
        logger.error(f"Failed to activate virtual environment: {e}")
        raise

def load_models():
    """Load F5-TTS and WhisperX models for warm inference."""
    try:
        # Import heavy ML modules (only available after environment setup)
        from f5tts_engine import F5TTSEngine
        from whisperx_engine import WhisperXEngine
        
        # Initialize engines with model caching
        f5tts_engine = F5TTSEngine()
        whisperx_engine = WhisperXEngine()
        
        logger.info("Models loaded successfully for warm inference")
        return f5tts_engine, whisperx_engine
        
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        logger.error(traceback.format_exc())
        raise

def process_request(job_input: Dict[str, Any]) -> Dict[str, Any]:
    """Process F5-TTS request with word-level timing and subtitle generation."""
    try:
        # Extract input parameters
        text = job_input.get("text")
        audio_url = job_input.get("audio_url")
        voice_reference_url = job_input.get("voice_reference_url")
        options = job_input.get("options", {})
        
        if not text:
            raise ValueError("Missing required parameter: text")
        if not voice_reference_url:
            raise ValueError("Missing required parameter: voice_reference_url")
            
        logger.info(f"Processing F5-TTS request for text length: {len(text)}")
        
        # Import processing modules
        from f5tts_engine import process_tts
        from whisperx_engine import generate_word_timings
        from subtitle_generator import create_ass_subtitles
        from s3_client import upload_audio_to_s3, download_audio_from_s3
        
        # Download reference voice if needed
        reference_audio_path = None
        if voice_reference_url:
            reference_audio_path = download_audio_from_s3(voice_reference_url)
            logger.info("Downloaded reference voice audio")
        
        # Generate speech with F5-TTS
        output_audio_path = process_tts(
            text=text,
            reference_audio_path=reference_audio_path
        )
        logger.info("Generated speech with F5-TTS")
        
        # Generate word-level timings if requested
        word_timings = None
        subtitles_url = None
        
        if options.get("create_subtitles", False):
            word_timings = generate_word_timings(output_audio_path, text)
            logger.info("Generated word-level timings")
            
            # Create ASS subtitles if requested
            if options.get("subtitle_format") == "ass":
                subtitles_path = create_ass_subtitles(word_timings, text)
                subtitles_url = upload_audio_to_s3(subtitles_path, "subtitles")
                logger.info("Created ASS subtitles")
        
        # Upload output audio to S3
        output_audio_url = upload_audio_to_s3(output_audio_path, "output")
        logger.info("Uploaded output audio to S3")
        
        # Prepare response
        response = {
            "audio_url": output_audio_url,
            "processing_time": None,  # TODO: Add timing
            "text_length": len(text),
            "success": True
        }
        
        if word_timings:
            response["word_timings"] = word_timings
            
        if subtitles_url:
            response["subtitles_url"] = subtitles_url
            
        logger.info("Request processed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Failed to process request: {e}")
        logger.error(traceback.format_exc())
        return {
            "error": str(e),
            "success": False
        }

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main RunPod serverless handler.
    
    Implements 2-layer architecture:
    1. Cold start: Setup network volume environment
    2. Warm loading: Use cached models for fast inference
    """
    try:
        logger.info("F5-TTS RunPod Serverless Handler v3.0 starting...")
        
        job_input = job.get("input", {})
        job_id = job.get("id", "unknown")
        
        logger.info(f"Processing job {job_id}")
        
        # Check if environment setup is required (cold start)
        if not check_setup_complete():
            logger.info("Cold start detected - setting up environment...")
            setup_environment()
        else:
            logger.info("Warm start - using existing environment")
            
        # Activate virtual environment with ML dependencies
        activate_virtual_environment()
        
        # Process the request
        result = process_request(job_input)
        
        logger.info(f"Job {job_id} completed")
        return {"output": result}
        
    except Exception as e:
        error_msg = f"Handler failed: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        return {
            "error": error_msg,
            "traceback": traceback.format_exc()
        }

# RunPod serverless entry point
if __name__ == "__main__":
    try:
        import runpod
        logger.info("Starting RunPod serverless worker...")
        runpod.serverless.start({"handler": handler})
    except ImportError:
        logger.error("RunPod library not available - running in test mode")
        # Test mode for local development
        test_job = {
            "id": "test-123",
            "input": {
                "text": "Hello world, this is a test.",
                "voice_reference_url": "s3://test-bucket/reference.wav",
                "options": {
                    "create_subtitles": True,
                    "subtitle_format": "ass"
                }
            }
        }
        result = handler(test_job)
        print(json.dumps(result, indent=2))