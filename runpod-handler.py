import runpod
import torch
import torchaudio
import librosa
import soundfile as sf
import numpy as np
import base64
import tempfile
import os
from typing import List, Optional
import time
from pydantic import BaseModel
import uuid
import json
from s3_utils import upload_to_s3, download_from_s3

# Prevent automatic pip installations during model loading
# This ensures flash_attn and other dependencies don't get installed twice
os.environ["PIP_NO_BUILD_ISOLATION"] = "1"
os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

# --- Data Models ---
class WordTiming(BaseModel):
    word: str
    start_time: float
    end_time: float

class TTSResponse(BaseModel):
    job_id: str
    status: str
    audio_url: Optional[str] = None
    word_timings: Optional[List[WordTiming]] = None
    duration: Optional[float] = None

# --- Job Management ---
jobs = {}

# --- Model Loading ---
model = None
device = "cuda" if torch.cuda.is_available() else "cpu"

def load_model():
    """Loads the F5-TTS model with optimized caching."""
    global model
    if model is not None:
        return model
    
    try:
        print(f"Loading F5-TTS model on {device}...")
        
        # Use the official F5-TTS API that comes with the container
        from f5_tts.api import F5TTS
        
        # Initialize with default model - the container has models pre-cached
        model = F5TTS(
            model="F5TTS_v1_Base",  # Use default F5TTS v1 base model
            ckpt_file="",           # Use default checkpoint
            vocab_file="",          # Use default vocab
            device=device,
            use_ema=True            # Use Exponential Moving Average for better quality
        )
        
        print(f"✅ F5-TTS model loaded successfully on {device}")
        
        # Upload models to S3 cache for future cold start optimization (async)
        try:
            from model_cache_init import upload_models_to_s3_cache
            import threading
            
            def upload_models_background():
                try:
                    upload_models_to_s3_cache()
                except Exception as e:
                    print(f"⚠️ Background model upload to S3 failed: {e}")
            
            # Upload models in background thread to not block startup
            upload_thread = threading.Thread(target=upload_models_background, daemon=True)
            upload_thread.start()
        except Exception as e:
            print(f"⚠️ Could not start background model upload: {e}")
        
        return model
        
    except Exception as e:
        print(f"❌ Error loading F5-TTS model: {e}")
        import traceback
        traceback.print_exc()
        model = None
        return None

# --- Helper Functions ---
def process_tts_job(job_id, text, speed, return_word_timings, local_voice):
    """Process TTS job with optimized error handling and cleanup."""
    temp_files = []
    
    try:
        jobs[job_id]["status"] = "PROCESSING"
        print(f"🔄 Processing job {job_id}: '{text[:50]}...'")

        # Ensure model is loaded
        current_model = load_model()
        if not current_model:
            raise Exception("Failed to load F5-TTS model")

        voice_path = None
        ref_text = None
        
        if local_voice:
            if local_voice.startswith("http"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_voice:
                    temp_files.append(temp_voice.name)
                    import requests
                    print(f"📥 Downloading voice from URL: {local_voice}")
                    r = requests.get(local_voice, timeout=30)
                    r.raise_for_status()
                    temp_voice.write(r.content)
                    temp_voice.flush()
                    voice_path = temp_voice.name
            else:
                voice_path = f"/tmp/{local_voice}"
                temp_files.append(voice_path)
                
                # Handle concurrent downloads with file locking and retry
                lock_file = f"{voice_path}.lock"
                max_retries = 3
                retry_delay = 1
                
                for attempt in range(max_retries):
                    try:
                        # Check if file already exists from another concurrent job
                        if os.path.exists(voice_path) and os.path.getsize(voice_path) > 0:
                            print(f"✅ Voice file already cached: {voice_path}")
                            break
                            
                        # Check if another job is downloading (lock file exists)
                        if os.path.exists(lock_file):
                            print(f"⏳ Another job downloading {local_voice}, waiting...")
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                            
                        # Create lock file to prevent concurrent downloads
                        with open(lock_file, 'w') as f:
                            f.write(f"locked_by_job_{job_id}")
                            
                        print(f"📥 Downloading voice from S3: voices/{local_voice}")
                        if download_from_s3(f"voices/{local_voice}", voice_path):
                            # Remove lock file on success
                            if os.path.exists(lock_file):
                                os.unlink(lock_file)
                            break
                        else:
                            # Remove lock file on failure
                            if os.path.exists(lock_file):
                                os.unlink(lock_file)
                            if attempt == max_retries - 1:
                                raise Exception(f"Failed to download voice: {local_voice}")
                            print(f"⚠️ Download attempt {attempt + 1} failed, retrying...")
                            time.sleep(retry_delay * (attempt + 1))
                            
                    except Exception as e:
                        # Clean up lock file on error
                        if os.path.exists(lock_file):
                            os.unlink(lock_file)
                        if attempt == max_retries - 1:
                            raise Exception(f"Failed to download voice after {max_retries} attempts: {local_voice} - {e}")
                        print(f"⚠️ Download attempt {attempt + 1} failed: {e}, retrying...")
                        time.sleep(retry_delay * (attempt + 1))
                
                # Try to download corresponding reference text file with concurrent protection
                text_filename = local_voice.replace('.wav', '.txt')
                text_path = f"/tmp/{text_filename}"
                temp_files.append(text_path)
                text_lock_file = f"{text_path}.lock"
                
                # Try to download text file with same protection
                for attempt in range(max_retries):
                    try:
                        # Check if text file already exists
                        if os.path.exists(text_path) and os.path.getsize(text_path) > 0:
                            print(f"✅ Reference text already cached: {text_path}")
                            break
                            
                        # Check if another job is downloading text file
                        if os.path.exists(text_lock_file):
                            print(f"⏳ Another job downloading {text_filename}, waiting...")
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                            
                        # Create text lock file
                        with open(text_lock_file, 'w') as f:
                            f.write(f"locked_by_job_{job_id}")
                            
                        print(f"📥 Attempting to download reference text: voices/{text_filename}")
                        if download_from_s3(f"voices/{text_filename}", text_path):
                            # Remove lock file on success
                            if os.path.exists(text_lock_file):
                                os.unlink(text_lock_file)
                            break
                        else:
                            # Remove lock file - text file is optional, don't fail
                            if os.path.exists(text_lock_file):
                                os.unlink(text_lock_file)
                            print(f"⚠️ No reference text found for {local_voice}")
                            break
                            
                    except Exception as e:
                        # Clean up text lock file on error
                        if os.path.exists(text_lock_file):
                            os.unlink(text_lock_file)
                        print(f"⚠️ Text download attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            print(f"⚠️ Could not download reference text after {max_retries} attempts")
                        else:
                            time.sleep(retry_delay * (attempt + 1))
                
                # Try to read the reference text if it exists
                if os.path.exists(text_path):
                    try:
                        with open(text_path, 'r', encoding='utf-8') as f:
                            ref_text = f.read().strip()
                        print(f"✅ Reference text loaded: {len(ref_text)} characters")
                    except Exception as e:
                        print(f"⚠️ Failed to read reference text: {e}")
                        ref_text = None
                else:
                    ref_text = None

        # Generate audio
        print(f"🎵 Generating audio with F5-TTS...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_files.append(temp_audio.name)
            
            # Use the model's infer method with correct parameter names
            infer_params = {
                "ref_file": voice_path,     # Reference audio file path
                "gen_text": text,           # Text to generate
                "speed": speed
            }
            
            # Add reference text if available (F5-TTS uses this for better voice cloning)
            if ref_text:
                infer_params["ref_text"] = ref_text
                print(f"🎯 Using reference text for better voice cloning")
            
            # F5TTS infer returns (wav, sample_rate, spectrogram)
            audio_data, sample_rate, _ = current_model.infer(**infer_params)
            
            # Write audio file with returned sample rate
            sf.write(temp_audio.name, audio_data, sample_rate)
            total_duration = len(audio_data) / sample_rate
            print(f"✅ Audio generated: {total_duration:.2f}s")

            # Calculate word timings if requested
            word_timings = []
            if return_word_timings:
                words = text.split()
                current_time = 0.0
                for word in words:
                    word_duration = max(0.2, len(word) * 0.08 / speed)
                    word_timings.append(WordTiming(
                        word=word,
                        start_time=current_time,
                        end_time=current_time + word_duration
                    ))
                    current_time += word_duration + 0.05

            # Upload to S3
            print(f"☁️ Uploading result to S3...")
            audio_url = upload_to_s3(temp_audio.name, f"output/{job_id}.wav")
            if not audio_url:
                raise Exception("Failed to upload audio to S3")

            # Update job status
            jobs[job_id]["status"] = "COMPLETED"
            jobs[job_id]["result"] = {
                "audio_url": audio_url,
                "word_timings": [wt.dict() for wt in word_timings],
                "duration": total_duration
            }
            print(f"✅ Job {job_id} completed successfully")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Job {job_id} failed: {error_msg}")
        jobs[job_id]["status"] = "ERROR"
        jobs[job_id]["error"] = error_msg
        
        # Log full traceback for debugging
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    print(f"🗑️ Cleaned up: {temp_file}")
            except Exception as cleanup_error:
                print(f"⚠️ Failed to cleanup {temp_file}: {cleanup_error}")

# --- RunPod Handler ---
def handler(job):
    """
    Optimized RunPod serverless handler for F5-TTS.
    """
    try:
        # Ensure model is loaded on first request
        current_model = load_model()
        if not current_model:
            return {"error": "TTS model failed to load"}

        job_input = job.get('input', {})
        endpoint = job_input.get("endpoint")
        
        # EXTENSIVE DEBUGGING for handler entry point
        print(f"🔍 HANDLER DEBUG:")
        print(f"🔍 Full job object: {job}")
        print(f"🔍 job_input: {job_input}")
        print(f"🔍 endpoint: '{endpoint}'")
        print(f"🔍 endpoint type: {type(endpoint)}")
        print(f"🎯 Handling request - endpoint: {endpoint}")

        if endpoint == "upload":
            # Voice file parameters
            voice_file_url = job_input.get("voice_file_url")
            voice_file = job_input.get("voice_file")  # base64
            voice_name = job_input.get("voice_name")
            
            # Reference text file parameters (text must be provided as file, not direct string)
            text_file_url = job_input.get("text_file_url")
            text_file = job_input.get("text_file")  # base64

            if not voice_name:
                return {"error": "voice_name is required for upload."}

            # Upload voice file
            voice_uploaded = False
            if voice_file_url:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                        import requests
                        print(f"📥 Downloading voice file from URL: {voice_file_url}")
                        r = requests.get(voice_file_url, timeout=60)
                        r.raise_for_status()
                        temp_file.write(r.content)
                        temp_file.flush()
                        if upload_to_s3(temp_file.name, f"voices/{voice_name}"):
                            voice_uploaded = True
                        os.unlink(temp_file.name)
                except Exception as e:
                    return {"error": f"Failed to download/upload voice file: {str(e)}"}
                    
            elif voice_file:
                # DEPRECATED: Base64 support will be removed in future versions
                print("⚠️ WARNING: Base64 file upload is deprecated. Use voice_file_url instead.")
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                        temp_file.write(base64.b64decode(voice_file))
                        temp_file.flush()
                        if upload_to_s3(temp_file.name, f"voices/{voice_name}"):
                            voice_uploaded = True
                        os.unlink(temp_file.name)
                except Exception as e:
                    return {"error": f"Failed to process voice file: {str(e)}"}
            else:
                return {"error": "Either voice_file or voice_file_url is required for upload."}

            # Upload reference text file (required for F5-TTS)
            text_uploaded = False
            text_filename = voice_name.replace('.wav', '.txt')
            
            if text_file_url:
                # Text file from URL
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
                        import requests
                        print(f"📥 Downloading text file from URL: {text_file_url}")
                        r = requests.get(text_file_url, timeout=30)
                        r.raise_for_status()
                        temp_file.write(r.content)
                        temp_file.flush()
                        if upload_to_s3(temp_file.name, f"voices/{text_filename}"):
                            text_uploaded = True
                        os.unlink(temp_file.name)
                except Exception as e:
                    return {"error": f"Failed to download/upload text file: {str(e)}"}
                    
            elif text_file:
                # DEPRECATED: Base64 support will be removed in future versions
                print("⚠️ WARNING: Base64 text file upload is deprecated. Use text_file_url instead.")
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
                        temp_file.write(base64.b64decode(text_file))
                        temp_file.flush()
                        if upload_to_s3(temp_file.name, f"voices/{text_filename}"):
                            text_uploaded = True
                        os.unlink(temp_file.name)
                except Exception as e:
                    return {"error": f"Failed to process text file: {str(e)}"}
            else:
                return {"error": "Reference text file is required. Provide text_file_url or text_file."}

            # Return success status
            if voice_uploaded and text_uploaded:
                return {"status": f"Voice '{voice_name}' and reference text uploaded successfully."}
            elif voice_uploaded:
                return {"error": "Voice file uploaded but reference text failed."}
            else:
                return {"error": "Failed to upload voice file."}

        elif endpoint == "status":
            job_id = job_input.get("job_id")
            if not job_id or job_id not in jobs:
                return {"error": "Invalid job_id."}
            return {"job_id": job_id, "status": jobs[job_id]["status"]}

        elif endpoint == "result":
            job_id = job_input.get("job_id")
            
            # EXTENSIVE DEBUGGING for result endpoint issue
            print(f"🔍 RESULT ENDPOINT DEBUG:")
            print(f"🔍 Raw job_input: {job_input}")
            print(f"🔍 Extracted job_id: '{job_id}'")
            print(f"🔍 job_id type: {type(job_id)}")
            print(f"🔍 All jobs in memory: {list(jobs.keys())}")
            print(f"🔍 Jobs detail: {jobs}")
            
            if not job_id:
                print("❌ RESULT DEBUG: No job_id provided")
                return {"error": "No job_id provided"}
                
            if job_id not in jobs:
                print(f"❌ RESULT DEBUG: job_id '{job_id}' not found in jobs")
                print(f"❌ Available jobs: {list(jobs.keys())}")
                return {"error": f"Invalid job_id: {job_id}"}
            
            print(f"🔍 Job found - status: {jobs[job_id]['status']}")
            print(f"🔍 Job data: {jobs[job_id]}")
            
            if jobs[job_id]["status"] != "COMPLETED":
                print(f"❌ RESULT DEBUG: Job not completed, status: {jobs[job_id]['status']}")
                return {"error": f"Job is not complete. Status: {jobs[job_id]['status']}"}
            
            # This should be the ONLY path for completed jobs
            print(f"✅ RESULT DEBUG: Returning cached result for job {job_id}")
            result = jobs[job_id]["result"]
            print(f"✅ RESULT DEBUG: Result data: {result}")
            return result
            
        elif endpoint == "list_voices":
            # List available voices in S3
            try:
                voices = []
                if s3_client and S3_BUCKET:
                    from s3_utils import s3_client, S3_BUCKET
                    response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix="voices/")
                    
                    if 'Contents' in response:
                        voice_files = {}
                        for obj in response['Contents']:
                            key = obj['Key']
                            filename = key.replace('voices/', '')
                            
                            if filename.endswith('.wav'):
                                voice_name = filename
                                text_name = filename.replace('.wav', '.txt')
                                voice_files[voice_name] = {
                                    'voice_file': voice_name,
                                    'text_file': None,
                                    'size': obj['Size'],
                                    'last_modified': obj['LastModified'].isoformat()
                                }
                            elif filename.endswith('.txt'):
                                voice_name = filename.replace('.txt', '.wav')
                                if voice_name in voice_files:
                                    voice_files[voice_name]['text_file'] = filename
                        
                        voices = list(voice_files.values())
                
                return {
                    "voices": voices,
                    "count": len(voices),
                    "status": "success"
                }
            except Exception as e:
                return {"error": f"Failed to list voices: {str(e)}"}

        else:  # Default to TTS generation
            # DEBUGGING: This should NOT be triggered for result endpoint!
            print(f"🚨 ELSE BLOCK TRIGGERED - THIS IS THE PROBLEM!")
            print(f"🚨 endpoint value: '{endpoint}'")
            print(f"🚨 This means 'result' endpoint is falling through to TTS generation!")
            print(f"🚨 job_input: {job_input}")
            
            text = job_input.get('text')
            speed = job_input.get('speed', 1.0)
            return_word_timings = job_input.get('return_word_timings', True)
            local_voice = job_input.get('local_voice')

            print(f"🚨 TTS params - text: '{text}', local_voice: '{local_voice}'")

            if not text:
                return {"error": "Text input is required."}

            job_id = str(uuid.uuid4())
            jobs[job_id] = {"status": "QUEUED"}
            
            print(f"🚨 CREATING NEW JOB: {job_id} (THIS SHOULD NOT HAPPEN FOR RESULT ENDPOINT)")

            # Run the job in the background
            import threading
            thread = threading.Thread(target=process_tts_job, args=(job_id, text, speed, return_word_timings, local_voice))
            thread.start()

            return {"job_id": job_id, "status": "QUEUED"}
            
    except Exception as e:
        error_msg = f"Handler error: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {"error": error_msg}

def cleanup_stale_locks():
    """Remove any stale lock files from previous sessions."""
    import glob
    try:
        lock_files = glob.glob("/tmp/*.lock")
        if lock_files:
            print(f"🧹 Cleaning up {len(lock_files)} stale lock files...")
            for lock_file in lock_files:
                try:
                    os.unlink(lock_file)
                    print(f"🗑️ Removed stale lock: {lock_file}")
                except Exception as e:
                    print(f"⚠️ Could not remove {lock_file}: {e}")
        else:
            print("✅ No stale lock files found")
    except Exception as e:
        print(f"⚠️ Lock cleanup error: {e}")

if __name__ == "__main__":
    print("🚀 Starting F5-TTS RunPod serverless worker...")
    
    # Clean up any stale lock files from previous sessions
    cleanup_stale_locks()
    
    # Pre-load model for faster first inference
    print("🔄 Pre-loading F5-TTS model...")
    load_model()
    
    print("✅ F5-TTS RunPod serverless worker ready!")
    runpod.serverless.start({"handler": handler})
