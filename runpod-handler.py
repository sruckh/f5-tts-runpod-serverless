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
            model_type="F5-TTS", 
            ckpt_file="",  # Use default model
            vocab_file="", # Use default vocab
            device=device
        )
        
        print(f"✅ F5-TTS model loaded successfully on {device}")
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

        # Generate audio
        print(f"🎵 Generating audio with F5-TTS...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_files.append(temp_audio.name)
            
            # Use the model's infer method
            audio_data = current_model.infer(
                text=text,
                ref_audio=voice_path,  # Updated parameter name
                speed=speed
            )
            
            # Write audio file
            sf.write(temp_audio.name, audio_data, 22050)
            total_duration = len(audio_data) / 22050
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
        
        print(f"🎯 Handling request - endpoint: {endpoint}")

        if endpoint == "upload":
            file_url = job_input.get("url_file")
            file = job_input.get("file")
            voice_name = job_input.get("voice_name")

            if not voice_name:
                return {"error": "voice_name is required for upload."}

            if file_url:
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    import requests
                    r = requests.get(file_url)
                    temp_file.write(r.content)
                    temp_file.flush()
                    upload_to_s3(temp_file.name, f"voices/{voice_name}")
                    os.unlink(temp_file.name)
            elif file:
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(base64.b64decode(file))
                    temp_file.flush()
                    upload_to_s3(temp_file.name, f"voices/{voice_name}")
                    os.unlink(temp_file.name)
            else:
                return {"error": "Either file or url_file is required for upload."}

            return {"status": f"Voice '{voice_name}' uploaded successfully."}

        elif endpoint == "status":
            job_id = job_input.get("job_id")
            if not job_id or job_id not in jobs:
                return {"error": "Invalid job_id."}
            return {"job_id": job_id, "status": jobs[job_id]["status"]}

        elif endpoint == "result":
            job_id = job_input.get("job_id")
            if not job_id or job_id not in jobs:
                return {"error": "Invalid job_id."}
            if jobs[job_id]["status"] != "COMPLETED":
                return {"error": f"Job is not complete. Status: {jobs[job_id]['status']}"}
            return jobs[job_id]["result"]

        else:  # Default to TTS generation
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
    
    # Pre-load model for faster first inference
    print("🔄 Pre-loading F5-TTS model...")
    load_model()
    
    print("✅ F5-TTS RunPod serverless worker ready!")
    runpod.serverless.start({"handler": handler})
