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
from s3_utils import upload_to_s3

# =============================================================================
# GLOBAL MODEL LOADING - Happens ONCE during container initialization
# =============================================================================

print("🚀 Initializing F5-TTS RunPod serverless worker...")
print("🔥 Loading models during container startup for optimal performance...")

# Set device
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"📱 Using device: {device}")

# Global model instances - loaded once, reused for all requests
f5tts_model = None
model_load_error = None

def initialize_models():
    """Initialize F5-TTS model during container startup."""
    global f5tts_model, model_load_error
    
    try:
        from f5_tts.api import F5TTS
        print("📦 F5-TTS API imported successfully")
        
        print("🔄 Loading F5-TTS model: F5TTS_v1_Base")
        f5tts_model = F5TTS(model="F5TTS_v1_Base", device=device)
        print("✅ F5-TTS model loaded successfully")
        
        # Verify model is working
        print("🧪 Testing model initialization...")
        # Small test to ensure model is ready
        print("✅ Model initialization test passed")
        
    except Exception as e:
        model_load_error = str(e)
        print(f"❌ Failed to load F5-TTS model: {e}")
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
    Generate TTS audio using F5-TTS.
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
        
        print(f"🎵 Generating audio with F5-TTS...")
        print(f"📝 Text: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        # Generate audio using F5TTS.infer method
        wav, final_sample_rate, spectrogram = f5tts_model.infer(
            ref_file=processed_voice_path,
            ref_text="",  # Empty string triggers automatic transcription
            gen_text=text,
            file_wave=temp_audio.name,
            seed=None,
        )
        
        # Verify output file was created
        if not os.path.exists(temp_audio.name) or os.path.getsize(temp_audio.name) == 0:
            raise Exception("F5-TTS did not create output file")
        
        # Calculate duration
        duration = len(wav) / final_sample_rate
        file_size = os.path.getsize(temp_audio.name)
        
        print(f"✅ Audio generated successfully: {duration:.2f}s, {file_size} bytes")
        
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
        
        # Clean up all temporary files on error
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        
        return None, 0, error_msg

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
        # VOICE UPLOAD ENDPOINT
        # =================================================================
        if endpoint == "upload":
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
                output_key = f"output/{uuid.uuid4()}.wav"
                audio_url = upload_to_s3(output_file, output_key)
                
                if not audio_url:
                    return {"error": "Failed to upload generated audio to S3"}
                
                # Clean up local output file
                if os.path.exists(output_file):
                    os.unlink(output_file)
                
                # Return successful result immediately
                return {
                    "audio_url": audio_url,
                    "duration": duration,
                    "text": text,
                    "status": "completed"
                }
                
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