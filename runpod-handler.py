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
    """Loads the F5-TTS model using the correct official API."""
    global model
    if model is not None:
        return model
    
    try:
        print(f"Loading F5-TTS model...")
        
        # Use the correct F5-TTS API from the official implementation
        from f5_tts.api import F5TTS
        
        # Initialize F5TTS with no parameters (uses defaults)
        model = F5TTS()
        
        print(f"✅ F5-TTS model loaded successfully")
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
                print(f"📥 Downloading voice from S3: voices/{local_voice}")
                if not download_from_s3(f"voices/{local_voice}", voice_path):
                    raise Exception(f"Failed to download voice: {local_voice}")
                
                # Try to download corresponding reference text file
                text_filename = local_voice.replace('.wav', '.txt')
                text_path = f"/tmp/{text_filename}"
                temp_files.append(text_path)
                print(f"📥 Attempting to download reference text: voices/{text_filename}")
                if download_from_s3(f"voices/{text_filename}", text_path):
                    try:
                        with open(text_path, 'r', encoding='utf-8') as f:
                            ref_text = f.read().strip()
                        print(f"✅ Reference text loaded: {len(ref_text)} characters")
                    except Exception as e:
                        print(f"⚠️ Failed to read reference text: {e}")
                        ref_text = None
                else:
                    print(f"⚠️ No reference text found for {local_voice}")

        # Preprocess reference audio to optimal length (3-10 seconds for F5-TTS)
        if voice_path:
            try:
                import librosa
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
                    import soundfile as sf
                    clipped_path = voice_path.replace('.wav', '_clipped.wav')
                    sf.write(clipped_path, audio_data_ref, sr_ref)
                    voice_path = clipped_path
                    temp_files.append(clipped_path)
                    print(f"✅ Clipped reference audio saved: {8.0:.1f}s")
                else:
                    print(f"✅ Reference audio duration optimal: {duration:.1f}s")
            except Exception as e:
                print(f"⚠️ Could not preprocess reference audio: {e}")

        # Generate audio using correct F5-TTS API
        print(f"🎵 Generating audio with F5-TTS...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_files.append(temp_audio.name)
            
            try:
                # Use the official F5-TTS API parameters
                print(f"🔄 Running F5-TTS inference with official API...")
                
                # Ensure we have required parameters
                if not voice_path:
                    raise Exception("Reference audio file is required for F5-TTS")
                
                # Set default ref_text if not provided - let F5-TTS transcribe
                if not ref_text:
                    ref_text = ""  # Empty string triggers ASR transcription
                    print(f"🎤 No reference text provided - F5-TTS will use ASR to transcribe reference audio")
                else:
                    print(f"🎯 Using provided reference text: {ref_text[:50]}...")
                
                # Call F5-TTS with correct parameters
                wav, sr, spec = current_model.infer(
                    ref_file=voice_path,
                    ref_text=ref_text,
                    gen_text=text,
                    file_wave=temp_audio.name  # Direct output to temp file
                )
                
                print(f"✅ F5-TTS inference successful - sample_rate: {sr}")
                
                # Verify output file was created
                if not os.path.exists(temp_audio.name):
                    raise Exception("F5-TTS did not create output file")
                
                # Get file info for logging
                file_size = os.path.getsize(temp_audio.name)
                audio_data, sample_rate = sf.read(temp_audio.name)
                total_duration = len(audio_data) / sample_rate
                
                print(f"✅ Audio generated: {total_duration:.2f}s, {file_size} bytes")
                
            except Exception as e:
                print(f"❌ F5-TTS inference failed: {e}")
                import traceback
                traceback.print_exc()
                raise Exception(f"F5-TTS inference failed: {str(e)}")

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
        job_input = job.get('input', {})
        endpoint = job_input.get("endpoint")
        
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
            if not job_id or job_id not in jobs:
                return {"error": "Invalid job_id."}
            
            job_status = jobs[job_id]["status"]
            if job_status == "ERROR":
                return {"error": f"Job failed: {jobs[job_id].get('error', 'Unknown error')}"}
            elif job_status != "COMPLETED":
                return {"error": f"Job is not complete. Status: {job_status}"}
            
            # Return successful result
            result = jobs[job_id].get("result")
            if not result:
                return {"error": "Job completed but no result found"}
            
            return result
            
        elif endpoint == "list_voices":
            # List available voices in S3
            try:
                voices = []
                from s3_utils import s3_client, S3_BUCKET
                if s3_client and S3_BUCKET:
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
            # Ensure model is loaded for TTS generation ONLY
            current_model = load_model()
            if not current_model:
                return {"error": "TTS model failed to load"}
            
            text = job_input.get('text')
            speed = job_input.get('speed', 1.0)
            return_word_timings = job_input.get('return_word_timings', True)
            local_voice = job_input.get('local_voice')

            if not text:
                return {"error": "Text input is required."}

            job_id = str(uuid.uuid4())
            jobs[job_id] = {"status": "QUEUED"}

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

if __name__ == "__main__":
    print("🚀 Starting F5-TTS RunPod serverless worker...")
    
    # Sync models from S3 for faster cold starts if enabled
    if os.environ.get("ENABLE_S3_MODEL_CACHE", "").lower() == "true":
        print("📥 Syncing models from S3 for faster cold starts...")
        try:
            from s3_utils import sync_models_from_s3
            
            # Use cache directory priority from optimization
            cache_dirs = [
                "/tmp/models",            # More space (10-20GB+) - preferred
                "/app/models",            # Container fallback
                "/runpod-volume/models"   # Limited space - last resort
            ]
            
            for cache_dir in cache_dirs:
                try:
                    if sync_models_from_s3(cache_dir):
                        print(f"✅ Models synced from S3 to {cache_dir}")
                        # Set environment variables for model loading
                        os.environ["HF_HOME"] = cache_dir
                        os.environ["TRANSFORMERS_CACHE"] = cache_dir
                        break
                except Exception as e:
                    print(f"⚠️ Failed to sync to {cache_dir}: {e}")
                    continue
            else:
                print("⚠️ S3 model sync failed for all cache directories")
                
        except Exception as e:
            print(f"⚠️ S3 model sync failed: {e}")
            # Continue startup even if S3 sync fails
    
    # Pre-load model for faster first inference
    print("🔄 Pre-loading F5-TTS model...")
    load_model()
    
    # Upload models to S3 for persistence if enabled
    if os.environ.get("ENABLE_S3_MODEL_CACHE", "").lower() == "true":
        print("☁️ Uploading models to S3 for persistence...")
        try:
            from s3_utils import upload_models_to_s3
            
            # Try multiple model cache directories
            model_dirs = [
                os.environ.get("HF_HOME", "/tmp/models"),
                os.environ.get("TRANSFORMERS_CACHE", "/tmp/models"),
                "/tmp/models",
                "/app/models",
                "/runpod-volume/models"
            ]
            
            for model_dir in model_dirs:
                if os.path.exists(model_dir) and os.listdir(model_dir):
                    print(f"📦 Found models in {model_dir}, uploading to S3...")
                    if upload_models_to_s3(model_dir):
                        print(f"✅ Models uploaded from {model_dir}")
                        break
                    else:
                        print(f"⚠️ Failed to upload models from {model_dir}")
            else:
                print("⚠️ No model directories found with content to upload")
                
        except Exception as e:
            print(f"⚠️ S3 model upload failed: {e}")
            # Continue startup even if S3 upload fails
    
    print("✅ F5-TTS RunPod serverless worker ready!")
    runpod.serverless.start({"handler": handler})
