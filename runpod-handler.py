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

def format_srt_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

def format_vtt_time(seconds):
    """Convert seconds to WebVTT time format (HH:MM:SS.mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

def generate_srt_from_timings(timing_entries):
    """Generate SRT format from timing entries"""
    srt_lines = []
    for i, entry in enumerate(timing_entries):
        start_srt = format_srt_time(entry["start_time"])
        end_srt = format_srt_time(entry["end_time"])
        srt_lines.append(f"{i+1}")
        srt_lines.append(f"{start_srt} --> {end_srt}")
        srt_lines.append(entry["word"])
        srt_lines.append("")  # Empty line separator
    return "
".join(srt_lines)
                    
                else:  # Default "json" format
                    # Original JSON format (for backwards compatibility)
                    for entry in timing_entries:
                        word_timings.append(WordTiming(
                            word=entry["word"],
                            start_time=entry["start_time"],
                            end_time=entry["end_time"]
                        ))
                    timing_data = word_timings

            # Upload to S3
            print(f"☁️ Uploading result to S3...")
            s3_upload_success = upload_to_s3(temp_audio.name, f"output/{job_id}.wav")
            if not s3_upload_success:
                raise Exception("Failed to upload audio to S3")
            
            # Generate serverless download URL instead of direct S3 URL
            # This ensures authentication and access control through the serverless function
            audio_url = f"/download?file_path=output/{job_id}.wav"
            print(f"✅ Audio uploaded to S3, serverless download URL: {audio_url}")

            # Update job status
            jobs[job_id]["status"] = "COMPLETED"
            # Prepare result with downloadable timing files
            result = {
                "audio_url": audio_url,
                "duration": total_duration
            }
            
            # Create timing files and upload to S3 for download
            if return_word_timings:
                timing_urls = {}
                
                if timing_format in ["srt", "vtt", "compact"]:
                    # Create and upload the requested format
                    file_extension = timing_format if timing_format != "compact" else "csv"
                    timing_filename = f"timings/{job_id}.{file_extension}"
                    
                    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix=f".{file_extension}") as timing_file:
                        timing_file.write(timing_data)
                        timing_file.flush()
                        
                        # Upload timing file to S3
                        if upload_to_s3(timing_file.name, timing_filename):
                            timing_urls[timing_format] = f"/download?file_path={timing_filename}"
                            print(f"✅ {timing_format.upper()} timing file uploaded: {timing_filename}")
                        
                        os.unlink(timing_file.name)
                        temp_files.append(timing_file.name)
                
                else:  # JSON format - create multiple formats for flexibility
                    # Generate and upload SRT format (most common for FFMPEG)
                    srt_data = generate_srt_from_timings(timing_entries)
                    srt_filename = f"timings/{job_id}.srt"
                    
                    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix=".srt") as srt_file:
                        srt_file.write(srt_data)
                        srt_file.flush()
                        
                        if upload_to_s3(srt_file.name, srt_filename):
                            timing_urls["srt"] = f"/download?file_path={srt_filename}"
                            print(f"✅ SRT timing file uploaded: {srt_filename}")
                        
                        os.unlink(srt_file.name)
                    
                    # Generate and upload compact CSV format
                    compact_data = generate_compact_from_timings(timing_entries)
                    csv_filename = f"timings/{job_id}.csv"
                    
                    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix=".csv") as csv_file:
                        csv_file.write(compact_data)
                        csv_file.flush()
                        
                        if upload_to_s3(csv_file.name, csv_filename):
                            timing_urls["compact"] = f"/download?file_path={csv_filename}"
                            print(f"✅ CSV timing file uploaded: {csv_filename}")
                        
                        os.unlink(csv_file.name)
                    
                    # Keep JSON for backwards compatibility (but no file - inline only)
                    result["word_timings"] = [wt.model_dump() for wt in word_timings]
                
                # Add download URLs to result
                if timing_urls:
                    result["timing_files"] = timing_urls
                    result["timing_format"] = timing_format
            
            jobs[job_id]["result"] = result
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
            
        elif endpoint == "download":
            # Download audio file with authentication through serverless
            file_path = job_input.get("file_path")
            
            if not file_path:
                return {"error": "file_path is required for download"}
            
            try:
                # Sanitize file path to prevent directory traversal
                import os.path
                file_path = os.path.normpath(file_path).replace("\", "/")
                if file_path.startswith("/") or ".." in file_path:
                    return {"error": "Invalid file path"}
                
                # Download from S3 to temporary file
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    if download_from_s3(file_path, temp_file.name):
                        # Read file content and return as base64
                        with open(temp_file.name, 'rb') as f:
                            file_content = f.read()
                        
                        # Clean up temp file
                        os.unlink(temp_file.name)
                        
                        # Return file content as base64 with proper MIME type
                        import base64
                        file_b64 = base64.b64encode(file_content).decode('utf-8')
                        
                        # Determine MIME type based on file extension
                        if file_path.endswith('.wav'):
                            mime_type = "audio/wav"
                        elif file_path.endswith('.srt'):
                            mime_type = "text/plain"
                        elif file_path.endswith('.vtt'):
                            mime_type = "text/vtt"
                        elif file_path.endswith('.csv'):
                            mime_type = "text/csv"
                        else:
                            mime_type = "application/octet-stream"
                        
                        return {
                            "success": True,
                            "file_content": file_b64,
                            "mime_type": mime_type,
                            "file_size": len(file_content),
                            "file_name": os.path.basename(file_path)
                        }
                    else:
                        return {"error": f"File not found in S3: {file_path}"}
            except Exception as e:
                return {"error": f"Download failed: {str(e)}"}
            
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
            timing_format = job_input.get('timing_format', 'json')  # json, srt, vtt, compact
            local_voice = job_input.get('local_voice')

            print(f"🚨 TTS params - text: '{text}', local_voice: '{local_voice}'")

            if not text:
                return {"error": "Text input is required."}

            job_id = str(uuid.uuid4())
            jobs[job_id] = {"status": "QUEUED"}
            
            print(f"🚨 CREATING NEW JOB: {job_id} (THIS SHOULD NOT HAPPEN FOR RESULT ENDPOINT)")

            # Run the job in the background
            import threading
            thread = threading.Thread(target=process_tts_job, args=(job_id, text, speed, return_word_timings, local_voice, timing_format))
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
