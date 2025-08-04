#!/usr/bin/env python3
"""
F5-TTS RunPod Serverless Handler - Proper Serverless Architecture
================================================================

This implementation follows RunPod serverless best practices:
- Synchronous processing (no threading)
- No job tracking or status endpoints
- Models loaded once during container initialization
- Direct result return
- Optimized for stateless execution
"""

import runpod
import torch
import torchaudio
import librosa
import soundfile as sf
import numpy as np
import tempfile
import os
import uuid
import requests
from typing import Optional
from s3_utils import upload_to_s3, download_file_from_s3_to_memory, upload_to_s3_with_presigned_url, generate_presigned_download_url
import base64
import json
# google.cloud.speech imported at runtime after installation

# =============================================================================
# GLOBAL MODEL LOADING - Happens ONCE during container initialization
# =============================================================================

print("🚀 Initializing F5-TTS RunPod serverless worker...")

# flash_attn will be checked during runtime installation

print("🔥 Loading models during container startup for optimal performance...")

# Set device
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"📱 Using device: {device}")

# Global model instances - loaded once, reused for all requests
f5tts_model = None
model_load_error = None

def initialize_models():
    """Initialize F5-TTS model with optimized runtime installation of heavy dependencies."""
    global f5tts_model, model_load_error
    
    try:
        print("🔄 Starting optimized warm import process...")
        
        # Smart package installation system
        def check_and_install_package(package_name, import_name=None, install_command=None, description=""):
            """Smart package detection and installation with disk space management."""
            import_name = import_name or package_name
            install_command = install_command or [package_name]
            
            try:
                # Try importing first
                if '.' in import_name:
                    # Handle nested imports like 'google.cloud.speech'
                    module_parts = import_name.split('.')
                    module = __import__(module_parts[0])
                    for part in module_parts[1:]:
                        module = getattr(module, part)
                else:
                    __import__(import_name)
                print(f"✅ {package_name} already available {description}")
                return True
            except ImportError:
                print(f"📦 Installing {package_name} at runtime {description}...")
                
                # Check available disk space before installation
                import shutil
                disk_usage = shutil.disk_usage("/")
                free_space_gb = disk_usage.free / (1024**3)
                
                if free_space_gb < 1.0:  # Less than 1GB free
                    print(f"⚠️ Low disk space: {free_space_gb:.2f}GB free. Cleaning up...")
                    cleanup_disk_space()
                    
                    # Recheck after cleanup
                    disk_usage = shutil.disk_usage("/")
                    free_space_gb = disk_usage.free / (1024**3)
                    
                    if free_space_gb < 0.5:  # Still less than 500MB
                        print(f"❌ Insufficient disk space: {free_space_gb:.2f}GB free. Skipping {package_name}")
                        return False
                
                try:
                    import subprocess
                    cmd = ["pip", "install", "--no-cache-dir"] + install_command
                    subprocess.check_call(cmd)
                    print(f"✅ {package_name} installed successfully")
                    return True
                except subprocess.CalledProcessError as e:
                    print(f"❌ Failed to install {package_name}: {e}")
                    return False
            except Exception as e:
                print(f"⚠️ {package_name} detection failed: {e}")
                return False
        
        def cleanup_disk_space():
            """Clean up temporary files and caches to free disk space."""
            import subprocess
            import os
            
            print("🧹 Cleaning up disk space...")
            cleanup_commands = [
                # Clear pip cache
                ["pip", "cache", "purge"],
                # Clear temporary files
                ["find", "/tmp", "-type", "f", "-delete", "2>/dev/null", "||", "true"],
                # Clear conda package cache
                ["conda", "clean", "-a", "-y"],
            ]
            
            for cmd in cleanup_commands:
                try:
                    subprocess.run(cmd, capture_output=True, check=False)
                except:
                    pass  # Ignore cleanup failures
            
            print("✅ Disk cleanup completed")
        
        # Optimized runtime installations with smart detection
        
        # 1. Install transformers (lightweight, always needed)
        transformers_success = check_and_install_package(
            "transformers", 
            install_command=["transformers>=4.48.1"],
            description="(HuggingFace transformers library)"
        )
        
        # 2. Install google-cloud-speech (optional, for timing fallback)
        gcs_success = check_and_install_package(
            "google-cloud-speech",
            import_name="google.cloud.speech", 
            description="(timing extraction fallback)"
        )
        
        # 3. Install flash_attn (large, GPU-optimized, use platform CUDA)
        flash_attn_success = check_and_install_package(
            "flash_attn",
            install_command=[
                # Use pip instead of precompiled wheel to avoid CUDA conflicts
                "flash-attn", "--no-build-isolation"
            ],
            description="(GPU-optimized attention)"
        )
        
        # 4. Install whisperx (large, for word-level timing)
        whisperx_success = check_and_install_package(
            "whisperx",
            description="(word-level timing extraction)"
        )
        
        # Report installation status
        print(f"📊 Package installation summary:")
        print(f"   • transformers: {'✅' if transformers_success else '❌'}")
        print(f"   • google-cloud-speech: {'✅' if gcs_success else '❌'}")
        print(f"   • flash_attn: {'✅' if flash_attn_success else '❌'}")
        print(f"   • whisperx: {'✅' if whisperx_success else '❌'}")
        
        # Verify critical dependencies
        try:
            import flash_attn
            flash_attn_version = getattr(flash_attn, '__version__', 'unknown')
            print(f"⚡ flash_attn v{flash_attn_version} - optimized attention enabled")
        except ImportError:
            print("⚠️ flash_attn not available - using standard attention (slower)")
        except Exception as e:
            print(f"⚠️ flash_attn detection failed: {e}")
        
        # Set environment variables for model caching on persistent volume
        model_cache_dir = "/runpod-volume/models"
        os.environ['HF_HOME'] = model_cache_dir
        os.environ['TRANSFORMERS_CACHE'] = model_cache_dir
        os.environ['HF_HUB_CACHE'] = os.path.join(model_cache_dir, 'hub')
        os.environ['TORCH_HOME'] = os.path.join(model_cache_dir, 'torch')
        
        # Ensure cache directories exist
        os.makedirs(os.environ['HF_HUB_CACHE'], exist_ok=True)
        os.makedirs(os.environ['TORCH_HOME'], exist_ok=True)

        # Import and initialize F5-TTS
        from f5_tts.api import F5TTS
        print("📦 F5-TTS API imported successfully")
        
        print(f"🔄 Loading F5-TTS model: F5TTS_v1_Base from {model_cache_dir}")
        f5tts_model = F5TTS(model="F5TTS_v1_Base", device=device)
        print("✅ F5-TTS model loaded successfully")
        
        # Verify model optimization parameters
        print("🧪 Testing model with optimized parameters...")
        
        import inspect
        infer_params = inspect.signature(f5tts_model.infer).parameters
        
        # Check for critical optimization parameters
        critical_params = ['nfe_step', 'cfg_strength', 'target_rms', 'cross_fade_duration', 'sway_sampling_coef', 'speed']
        supported_params = [param for param in critical_params if param in infer_params]
        unsupported_params = [param for param in critical_params if param not in infer_params]
        
        if supported_params:
            print(f"✅ Supported optimization parameters: {', '.join(supported_params)}")
            
        if unsupported_params:
            print(f"⚠️ Unsupported parameters (using defaults): {', '.join(unsupported_params)}")
            print("💡 Audio quality optimization may be limited by F5TTS API version")
        
        # Final disk space report
        import shutil
        disk_usage = shutil.disk_usage("/")
        free_space_gb = disk_usage.free / (1024**3)
        print(f"💾 Remaining disk space: {free_space_gb:.2f}GB")
        
        print("✅ Optimized warm import process completed successfully")
        
    except Exception as e:
        model_load_error = str(e)
        print(f"❌ Failed to load F5-TTS model: {e}")
        import traceback
        traceback.print_exc()
        print("⚠️ Serverless worker will return errors for TTS requests")

# Initialize models when module loads
initialize_models()

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def download_voice_file(voice_input: Optional[str]) -> Optional[str]:
    """
    Download voice file from URL or S3.
    Returns local file path or None if failed.
    """
    if not voice_input:
        return None
    
    try:
        # Create temporary file
        temp_voice = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_voice.close()
        
        if voice_input.startswith("http"):
            # Download from URL
            print(f"📥 Downloading voice from URL: {voice_input}")
            response = requests.get(voice_input, timeout=30)
            response.raise_for_status()
            
            with open(temp_voice.name, 'wb') as f:
                f.write(response.content)
                
        else:
            # Download from S3
            from s3_utils import download_from_s3
            print(f"📥 Downloading voice from S3: voices/{voice_input}")
            if not download_from_s3(f"voices/{voice_input}", temp_voice.name):
                raise Exception(f"Failed to download voice from S3: {voice_input}")
        
        # Verify file exists and is valid
        if not os.path.exists(temp_voice.name) or os.path.getsize(temp_voice.name) == 0:
            raise Exception("Downloaded voice file is empty or invalid")
        
        print(f"✅ Voice file downloaded: {os.path.getsize(temp_voice.name)} bytes")
        return temp_voice.name
        
    except Exception as e:
        print(f"❌ Failed to download voice file: {e}")
        if os.path.exists(temp_voice.name):
            os.unlink(temp_voice.name)
        return None

def preprocess_reference_audio(voice_path: str) -> str:
    """
    Preprocess reference audio for optimal F5-TTS performance.
    Returns path to processed audio file.
    """
    try:
        # Load audio and check duration
        audio_data_ref, sr_ref = librosa.load(voice_path, sr=None)
        duration = len(audio_data_ref) / sr_ref
        
        # If audio is longer than 10 seconds, clip to middle 8 seconds for best voice characteristics
        if duration > 10.0:
            print(f"⚠️ Reference audio is {duration:.1f}s, clipping to 8s for optimal voice cloning")
            start_sample = int((len(audio_data_ref) - 8 * sr_ref) / 2)
            end_sample = start_sample + int(8 * sr_ref)
            audio_data_ref = audio_data_ref[start_sample:end_sample]
            
            # Save clipped audio
            clipped_path = voice_path.replace('.wav', '_clipped.wav')
            sf.write(clipped_path, audio_data_ref, sr_ref)
            print(f"✅ Clipped reference audio saved: 8.0s")
            return clipped_path
        else:
            print(f"✅ Reference audio duration optimal: {duration:.1f}s")
            return voice_path
            
    except Exception as e:
        print(f"⚠️ Could not preprocess reference audio: {e}")
        return voice_path

def generate_tts_audio(text: str, voice_path: Optional[str] = None, speed: float = 1.0) -> tuple:
    """
    Generate TTS audio using F5-TTS with optimized parameters for stable, high-quality output.
    Returns (output_file_path, duration, error_message)
    """
    if model_load_error:
        return None, 0, f"Model not available: {model_load_error}"
    
    if not f5tts_model:
        return None, 0, "F5-TTS model not initialized"
    
    temp_files = []
    
    try:
        # Create output file
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_audio.close()
        temp_files.append(temp_audio.name)
        
        # Process reference audio if provided
        processed_voice_path = None
        if voice_path:
            processed_voice_path = preprocess_reference_audio(voice_path)
            if processed_voice_path != voice_path:
                temp_files.append(processed_voice_path)
        
        print(f"🎵 Generating audio with F5-TTS (optimized parameters)...")
        print(f"📝 Text: {text[:100]}{'...' if len(text) > 100 else ''}")
        print(f"⚡ Parameters: nfe_step=32, cfg_strength=2.0, target_rms=0.1, speed={speed}")
        
        # Prepare optimized parameters for stable, high-quality audio generation
        # These match the F5-TTS CLI defaults to prevent erratic behavior
        optimized_params = {
            "ref_file": processed_voice_path,
            "ref_text": "",  # Empty string triggers automatic transcription
            "gen_text": text,
            "file_wave": temp_audio.name,
            "seed": 42,  # Fixed seed for reproducible results
        }
        
        # Add optimization parameters if supported by the F5TTS API version
        try:
            import inspect
            infer_params = inspect.signature(f5tts_model.infer).parameters
            
            # Critical parameters for preventing audio artifacts
            if 'nfe_step' in infer_params:
                optimized_params['nfe_step'] = 32  # High-quality denoising (prevents speed/pitch artifacts)
                
            if 'cfg_strength' in infer_params:
                optimized_params['cfg_strength'] = 2.0  # Stable classifier guidance
                
            if 'target_rms' in infer_params:
                optimized_params['target_rms'] = 0.1  # Audio normalization (prevents volume jumps)
                
            if 'cross_fade_duration' in infer_params:
                optimized_params['cross_fade_duration'] = 0.15  # Smooth segment transitions
                
            if 'sway_sampling_coef' in infer_params:
                optimized_params['sway_sampling_coef'] = -1.0  # Stable sampling coefficient
                
            if 'speed' in infer_params:
                optimized_params['speed'] = speed  # User-controlled playback speed
                
        except Exception as param_error:
            print(f"⚠️ Parameter detection failed, using basic parameters: {param_error}")
        
        # Generate audio with optimized parameters
        print(f"🔧 Using {len(optimized_params)} parameters for high-quality generation")
        wav, final_sample_rate, spectrogram = f5tts_model.infer(**optimized_params)
        
        # Verify output file was created
        if not os.path.exists(temp_audio.name) or os.path.getsize(temp_audio.name) == 0:
            raise Exception("F5-TTS did not create output file")
        
        # Calculate duration
        duration = len(wav) / final_sample_rate
        file_size = os.path.getsize(temp_audio.name)
        
        print(f"✅ High-quality audio generated: {duration:.2f}s, {file_size} bytes")
        print(f"🔧 Applied optimization parameters to prevent erratic audio behavior")
        
        # Clean up temporary reference files (keep output file)
        for temp_file in temp_files[1:]:  # Skip the output file
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        
        return temp_audio.name, duration, None
        
    except Exception as e:
        error_msg = f"F5-TTS inference failed: {str(e)}"
        print(f"❌ {error_msg}")
        
        # Fallback: try with minimal parameters if optimized version fails
        if "unexpected keyword argument" in str(e) or "got an unexpected keyword argument" in str(e):
            print("🔄 Trying fallback with basic parameters...")
            try:
                wav, final_sample_rate, spectrogram = f5tts_model.infer(
                    ref_file=processed_voice_path,
                    ref_text="",
                    gen_text=text,
                    file_wave=temp_audio.name,
                    seed=42,
                )
                
                if os.path.exists(temp_audio.name) and os.path.getsize(temp_audio.name) > 0:
                    duration = len(wav) / final_sample_rate
                    print(f"⚠️ Fallback successful: {duration:.2f}s (limited optimization)")
                    return temp_audio.name, duration, None
                    
            except Exception as fallback_error:
                print(f"❌ Fallback also failed: {fallback_error}")
        
        # Clean up all temporary files on error
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        
        return None, 0, error_msg

def _get_google_speech_client():
    """
    Initialize Google Speech client securely using environment variables.
    Returns Google Speech client or None if credentials not available.
    """
    try:
        # Method 1: Service account JSON content from environment variable (RECOMMENDED)
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if credentials_json:
            from google.oauth2 import service_account
            import json
            
            print("🔐 Initializing Google Speech client with service account credentials")
            
            # Validate JSON before parsing
            if not credentials_json.strip().startswith('{'):
                print("❌ GOOGLE_CREDENTIALS_JSON must contain JSON content, not a file path")
                print("   Expected: '{\"type\":\"service_account\",...}'")
                print(f"   Got: {credentials_json[:50]}...")
                return None
            
            try:
                credentials_info = json.loads(credentials_json)
                
                # Validate required fields
                required_fields = ['type', 'project_id', 'private_key', 'client_email']
                missing_fields = [field for field in required_fields if field not in credentials_info]
                if missing_fields:
                    print(f"❌ Missing required fields in service account JSON: {missing_fields}")
                    return None
                
                if credentials_info.get('type') != 'service_account':
                    print(f"❌ Invalid credential type: {credentials_info.get('type')}. Expected: service_account")
                    return None
                    
                credentials = service_account.Credentials.from_service_account_info(credentials_info)
                from google.cloud import speech
                client = speech.SpeechClient(credentials=credentials)
                print(f"✅ Google Speech client initialized for project: {credentials_info['project_id']}")
                return client
                
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON in GOOGLE_CREDENTIALS_JSON: {e}")
                print("   Ensure the environment variable contains properly escaped JSON content")
                return None
        
        # Method 2: Service account file path (fallback for development)
        credentials_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_file and os.path.exists(credentials_file):
            print(f"🔧 Using service account file: {credentials_file}")
            from google.cloud import speech
            return speech.SpeechClient()
        
        # Method 3: Default application credentials (for Google Cloud environments)
        try:
            print("🔍 Attempting to use default application credentials...")
            from google.cloud import speech
            client = speech.SpeechClient()
            print("✅ Using default application credentials")
            return client
        except Exception:
            pass
        
        print("⚠️ No Google Cloud credentials found. Timing features will be disabled.")
        print("   To enable timing features, set one of:")
        print("   - GOOGLE_CREDENTIALS_JSON: Service account JSON content")
        print("   - GOOGLE_APPLICATION_CREDENTIALS: Path to service account file")
        return None
        
    except Exception as e:
        print(f"❌ Failed to initialize Google Speech client: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_word_timings(audio_file_path: str, text: str) -> Optional[dict]:
    """
    Extract word-level timings using Google Cloud Speech-to-Text.
    Returns timing data with word-level timestamps or None if failed.
    """
    try:
        print("🎙️ Extracting word timings using Google Speech API...")
        
        # Initialize Google Speech client securely
        client = _get_google_speech_client()
        if not client:
            print("❌ Google Speech client not available - credentials not configured")
            return None
        
        # Read the audio file
        with open(audio_file_path, 'rb') as audio_file:
            content = audio_file.read()
            
        # Configure the audio settings
        from google.cloud import speech
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,  # F5-TTS output sample rate
            language_code="en-US",
            enable_word_time_offsets=True,  # Critical for word-level timing
            enable_automatic_punctuation=True,
            model="latest_long",  # Best model for accuracy
        )
        
        # Perform the speech recognition
        print("🔍 Analyzing audio for word timings...")
        response = client.recognize(config=config, audio=audio)
        
        if not response.results:
            print("⚠️ No speech recognition results returned")
            return None
            
        # Extract word-level timing data
        words = []
        for result in response.results:
            alternative = result.alternatives[0]
            
            for word_info in alternative.words:
                # Handle different timing formats (Duration vs timedelta vs protobuf)
                start_time = 0.0
                end_time = 0.0
                
                # Convert start_time to float seconds
                if hasattr(word_info.start_time, 'total_seconds'):
                    # datetime.timedelta object
                    start_time = word_info.start_time.total_seconds()
                elif hasattr(word_info.start_time, 'seconds'):
                    # Google protobuf Duration object
                    start_time = word_info.start_time.seconds
                    if hasattr(word_info.start_time, 'nanos'):
                        start_time += word_info.start_time.nanos * 1e-9
                elif hasattr(word_info.start_time, 'microseconds'):
                    # Alternative timedelta format
                    start_time = word_info.start_time.total_seconds()
                else:
                    # Try direct conversion if it's already a number
                    try:
                        start_time = float(word_info.start_time)
                    except (TypeError, ValueError):
                        print(f"⚠️ Unknown start_time format: {type(word_info.start_time)} - {word_info.start_time}")
                        continue
                
                # Convert end_time to float seconds
                if hasattr(word_info.end_time, 'total_seconds'):
                    # datetime.timedelta object
                    end_time = word_info.end_time.total_seconds()
                elif hasattr(word_info.end_time, 'seconds'):
                    # Google protobuf Duration object
                    end_time = word_info.end_time.seconds
                    if hasattr(word_info.end_time, 'nanos'):
                        end_time += word_info.end_time.nanos * 1e-9
                elif hasattr(word_info.end_time, 'microseconds'):
                    # Alternative timedelta format
                    end_time = word_info.end_time.total_seconds()
                else:
                    # Try direct conversion if it's already a number
                    try:
                        end_time = float(word_info.end_time)
                    except (TypeError, ValueError):
                        print(f"⚠️ Unknown end_time format: {type(word_info.end_time)} - {word_info.end_time}")
                        continue
                
                word = {
                    'word': word_info.word,
                    'start_time': start_time,
                    'end_time': end_time,
                    'confidence': alternative.confidence
                }
                words.append(word)
        
        timing_data = {
            'words': words,
            'full_text': ' '.join([w['word'] for w in words]),
            'total_duration': words[-1]['end_time'] if words else 0,
            'confidence': response.results[0].alternatives[0].confidence if response.results else 0
        }
        
        print(f"✅ Extracted {len(words)} word timings (duration: {timing_data['total_duration']:.2f}s)")
        return timing_data
        
    except Exception as e:
        print(f"❌ Failed to extract word timings: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_word_timings_whisperx(audio_file_path: str, text: str) -> Optional[dict]:
    """
    Extract word-level timings using WhisperX for more accurate alignment.
    Returns timing data with word-level timestamps or None if failed.
    """
    try:
        print("🎙️ Extracting word timings using WhisperX...")
        
        import whisperx
        import gc
        import torch
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        batch_size = 16
        compute_type = "float16" if device == "cuda" else "int8"
        
        # 1. Load WhisperX model
        print("📦 Loading WhisperX model...")
        model = whisperx.load_model("large-v2", device, compute_type=compute_type)
        
        # 2. Load and transcribe audio
        print("🔍 Transcribing audio with WhisperX...")
        audio = whisperx.load_audio(audio_file_path)
        result = model.transcribe(audio, batch_size=batch_size)
        
        # 3. Load alignment model and align transcript to audio
        print("⚡ Performing forced alignment for precise word timings...")
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
        
        # 4. Clean up models to free GPU memory
        del model
        del model_a
        gc.collect()
        torch.cuda.empty_cache()
        
        # 5. Extract word-level timing data
        words = []
        for segment in result["segments"]:
            if "words" in segment:
                for word_info in segment["words"]:
                    word = {
                        'word': word_info['word'],
                        'start_time': word_info['start'],
                        'end_time': word_info['end'],
                        'confidence': word_info.get('score', 1.0)  # WhisperX uses 'score' for confidence
                    }
                    words.append(word)
        
        if not words:
            print("⚠️ No word timings extracted from WhisperX")
            return None
        
        timing_data = {
            'words': words,
            'full_text': ' '.join([w['word'] for w in words]),
            'total_duration': words[-1]['end_time'] if words else 0,
            'confidence': sum(w['confidence'] for w in words) / len(words) if words else 0,
            'language': result.get("language", "en"),
            'method': 'whisperx'
        }
        
        print(f"✅ WhisperX extracted {len(words)} word timings (duration: {timing_data['total_duration']:.2f}s)")
        print(f"🌐 Detected language: {timing_data['language']}")
        return timing_data
        
    except Exception as e:
        print(f"❌ Failed to extract word timings with WhisperX: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_timing_formats(timing_data: dict, job_id: str) -> dict:
    """
    Generate multiple timing file formats from timing data.
    Returns dict with format_name -> file_content mappings.
    """
    try:
        words = timing_data['words']
        formats = {}
        
        # SRT Format (SubRip)
        srt_content = ""
        for i, word in enumerate(words, 1):
            start_time = format_srt_time(word['start_time'])
            end_time = format_srt_time(word['end_time'])
            srt_content += f"{i}\n{start_time} --> {end_time}\n{word['word']}\n\n"
        formats['srt'] = srt_content
        
        # VTT Format (WebVTT)
        vtt_content = "WEBVTT\n\n"
        for word in words:
            start_time = format_vtt_time(word['start_time'])
            end_time = format_vtt_time(word['end_time'])
            vtt_content += f"{start_time} --> {end_time}\n{word['word']}\n\n"
        formats['vtt'] = vtt_content
        
        # CSV Format
        csv_content = "word,start_time,end_time,confidence\n"
        for word in words:
            csv_content += f"{word['word']},{word['start_time']:.3f},{word['end_time']:.3f},{word['confidence']:.3f}\n"
        formats['csv'] = csv_content
        
        # JSON Format
        json_content = json.dumps({
            'job_id': job_id,
            'timing_data': timing_data,
            'generated_at': str(uuid.uuid4())
        }, indent=2)
        formats['json'] = json_content
        
        # ASS Format (Advanced SubStation Alpha) - Better for FFMPEG
        ass_content = generate_ass_format(words)
        formats['ass'] = ass_content
        
        print(f"✅ Generated {len(formats)} timing formats: {list(formats.keys())}")
        return formats
        
    except Exception as e:
        print(f"❌ Failed to generate timing formats: {e}")
        return {}

def format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def format_vtt_time(seconds: float) -> str:
    """Format seconds as VTT timestamp (HH:MM:SS.mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"

def generate_ass_format(words: list) -> str:
    """Generate ASS format for advanced FFMPEG subtitle integration."""
    ass_header = """[Script Info]
Title: F5-TTS Generated Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = ""
    for word in words:
        start_time = format_ass_time(word['start_time'])
        end_time = format_ass_time(word['end_time'])
        events += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{word['word']}\n"
    
    return ass_header + events

def format_ass_time(seconds: float) -> str:
    """Format seconds as ASS timestamp (H:MM:SS.mm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

def upload_timing_files(timing_formats: dict, job_id: str) -> dict:
    """
    Upload timing files to S3 and return presigned download URLs.
    Returns dict with format_name -> presigned_download_url mappings.
    """
    try:
        timing_urls = {}
        
        for format_name, content in timing_formats.items():
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=f'.{format_name}')
            temp_file.write(content)
            temp_file.close()
            
            try:
                # Upload to S3 and generate presigned URL (1 hour expiration)
                s3_key = f"timings/{job_id}.{format_name}"
                presigned_url = upload_to_s3_with_presigned_url(temp_file.name, s3_key, expiration=3600)
                
                if presigned_url:
                    timing_urls[format_name] = presigned_url
                    print(f"✅ Uploaded {format_name} timing file with presigned URL: {s3_key}")
                else:
                    print(f"❌ Failed to upload {format_name} timing file")
                    
            finally:
                # Clean up temp file
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
        
        return timing_urls
        
    except Exception as e:
        print(f"❌ Failed to upload timing files: {e}")
        return {}

# =============================================================================
# RUNPOD SERVERLESS HANDLER - Synchronous Processing
# =============================================================================

def handler(job):
    """
    RunPod serverless handler for F5-TTS.
    Processes requests synchronously and returns results immediately.
    
    No threading, no job tracking, no status endpoints.
    """
    try:
        job_input = job.get('input', {})
        endpoint = job_input.get("endpoint", "tts")  # Default to TTS generation
        
        print(f"🎯 Processing request - endpoint: {endpoint}")
        
        # =================================================================
        # DOWNLOAD ENDPOINT
        # =================================================================
        if endpoint == "download":
            job_id = job_input.get("job_id")
            file_type = job_input.get("type", "audio")  # Default to audio
            file_format = job_input.get("format", "wav")  # Default format
            
            if not job_id:
                return {"error": "job_id is required for download"}

            try:
                if file_type == "timing":
                    # Download timing file
                    timing_key = f"timings/{job_id}.{file_format}"
                    timing_data = download_file_from_s3_to_memory(timing_key)
                    
                    if timing_data:
                        # Determine content type based on format
                        content_types = {
                            'srt': 'text/plain',
                            'vtt': 'text/vtt',
                            'csv': 'text/csv',
                            'json': 'application/json',
                            'ass': 'text/plain'
                        }
                        content_type = content_types.get(file_format, 'text/plain')
                        
                        return {
                            "timing_data": base64.b64encode(timing_data).decode('utf-8'),
                            "content_type": content_type,
                            "format": file_format,
                            "filename": f"{job_id}.{file_format}"
                        }
                    else:
                        return {"error": f"Timing file not found for job_id: {job_id}, format: {file_format}"}
                        
                else:
                    # Download audio file (default behavior)
                    output_key = f"output/{job_id}.wav"
                    audio_data = download_file_from_s3_to_memory(output_key)
                    
                    if audio_data:
                        return {
                            "audio_data": base64.b64encode(audio_data).decode('utf-8'),
                            "content_type": "audio/wav",
                            "filename": f"{job_id}.wav"
                        }
                    else:
                        return {"error": f"Audio file not found for job_id: {job_id}"}
                        
            except Exception as e:
                return {"error": f"Failed to download file: {str(e)}"}

        # =================================================================
        # VOICE UPLOAD ENDPOINT
        # =================================================================
        elif endpoint == "upload":
            voice_file_url = job_input.get("voice_file_url")
            voice_name = job_input.get("voice_name")
            
            if not voice_name:
                return {"error": "voice_name is required for upload"}
            
            if not voice_file_url:
                return {"error": "voice_file_url is required for upload"}
            
            # Download and upload voice file
            try:
                temp_voice = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_voice.close()
                
                print(f"📥 Downloading voice file from URL: {voice_file_url}")
                response = requests.get(voice_file_url, timeout=60)
                response.raise_for_status()
                
                with open(temp_voice.name, 'wb') as f:
                    f.write(response.content)
                
                # Upload to S3
                if upload_to_s3(temp_voice.name, f"voices/{voice_name}"):
                    os.unlink(temp_voice.name)
                    return {
                        "status": f"Voice '{voice_name}' uploaded successfully", 
                        "message": "F5-TTS will automatically transcribe the reference audio"
                    }
                else:
                    os.unlink(temp_voice.name)
                    return {"error": "Failed to upload voice file to S3"}
                    
            except Exception as e:
                if os.path.exists(temp_voice.name):
                    os.unlink(temp_voice.name)
                return {"error": f"Failed to process voice upload: {str(e)}"}
        
        # =================================================================
        # LIST VOICES ENDPOINT
        # =================================================================
        elif endpoint == "list_voices":
            try:
                from s3_utils import s3_client, S3_BUCKET
                
                if not s3_client or not S3_BUCKET:
                    return {"error": "S3 not configured"}
                
                response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix="voices/")
                voices = []
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        filename = key.replace('voices/', '')
                        
                        if filename.endswith('.wav') and filename:
                            voices.append({
                                'name': filename,
                                'size': obj['Size'],
                                'last_modified': obj['LastModified'].isoformat()
                            })
                
                return {
                    "voices": voices,
                    "count": len(voices),
                    "status": "success"
                }
                
            except Exception as e:
                return {"error": f"Failed to list voices: {str(e)}"}
        
        # =================================================================
        # TTS GENERATION ENDPOINT (Default)
        # =================================================================
        else:
            text = job_input.get('text')
            speed = job_input.get('speed', 1.0)
            local_voice = job_input.get('local_voice')
            return_word_timings = job_input.get('return_word_timings', False)
            timing_format = job_input.get('timing_format', 'srt')  # Default to SRT
            timing_method = job_input.get('timing_method', 'whisperx')  # Default to WhisperX
            
            if not text:
                return {"error": "Text input is required"}
            
            print(f"🎯 Generating TTS for text: {text[:100]}{'...' if len(text) > 100 else ''}")
            
            # Download voice file if specified
            voice_path = None
            if local_voice:
                voice_path = download_voice_file(local_voice)
                if not voice_path:
                    return {"error": f"Failed to download voice file: {local_voice}"}
            
            # Generate TTS audio
            output_file, duration, error = generate_tts_audio(text, voice_path, speed)
            
            # Clean up voice file
            if voice_path and os.path.exists(voice_path):
                os.unlink(voice_path)
            
            if error:
                return {"error": error}
            
            # Upload result to S3
            try:
                job_id = str(uuid.uuid4())
                output_key = f"output/{job_id}.wav"
                
                # Upload to S3 and generate secure presigned URL (1 hour expiration)
                audio_url = upload_to_s3_with_presigned_url(output_file, output_key, expiration=3600)
                
                if not audio_url:
                    return {"error": "Failed to upload generated audio to S3"}
                
                # Process timing data if requested
                timing_files = {}
                if return_word_timings:
                    print(f"🎯 Processing word timings (method: {timing_method}, format: {timing_format})...")
                    
                    # Extract word timings using selected method
                    if timing_method.lower() == 'google':
                        print("🔍 Using Google Speech API for timing extraction...")
                        timing_data = extract_word_timings(output_file, text)
                    else:  # Default to whisperx
                        print("🎙️ Using WhisperX for timing extraction...")
                        timing_data = extract_word_timings_whisperx(output_file, text)
                        
                        # Fallback to Google Speech API if WhisperX fails
                        if not timing_data:
                            print("🔄 WhisperX failed, trying Google Speech API fallback...")
                            timing_data = extract_word_timings(output_file, text)
                    
                    if timing_data:
                        # Generate timing formats
                        timing_formats = generate_timing_formats(timing_data, job_id)
                        
                        if timing_formats:
                            # Upload timing files to S3 and get download URLs
                            timing_files = upload_timing_files(timing_formats, job_id)
                            
                            if timing_files:
                                print(f"✅ Generated timing files: {list(timing_files.keys())}")
                            else:
                                print("⚠️ Failed to upload timing files to S3")
                        else:
                            print("⚠️ Failed to generate timing file formats")
                    else:
                        print("⚠️ Failed to extract word timings from audio")
                
                # Clean up local output file
                if os.path.exists(output_file):
                    os.unlink(output_file)
                
                # Build response with timing data if available
                response = {
                    "audio_url": audio_url,
                    "duration": duration,
                    "text": text,
                    "status": "completed",
                    "job_id": job_id
                }
                
                # Add timing files if they were generated
                if timing_files:
                    response["timing_files"] = timing_files
                    response["timing_format"] = timing_format
                    response["timing_method"] = timing_data.get('method', timing_method)
                    response["word_count"] = len(timing_data.get('words', []))
                    response["timing_confidence"] = timing_data.get('confidence', 0)
                
                return response
                
            except Exception as e:
                # Clean up on error
                if output_file and os.path.exists(output_file):
                    os.unlink(output_file)
                return {"error": f"Failed to process result: {str(e)}"}
    
    except Exception as e:
        error_msg = f"Handler error: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {"error": error_msg}

# =============================================================================
# RUNPOD SERVERLESS STARTUP
# =============================================================================

if __name__ == "__main__":
    print("✅ F5-TTS RunPod serverless worker ready!")
    print("🎯 Architecture: Synchronous processing with immediate results")
    print("⚡ Models pre-loaded for optimal performance")
    
    # Start RunPod serverless worker
    runpod.serverless.start({"handler": handler})