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
            model="F5TTS_v1_Base",  # Use default F5TTS v1 base model
            ckpt_file="",           # Use default checkpoint
            vocab_file="",          # Use default vocab
            device=device,
            use_ema=True            # Use Exponential Moving Average for better quality
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

        # Generate audio
        print(f"🎵 Generating audio with F5-TTS...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_files.append(temp_audio.name)
            
            # Use the model's inference method with version-compatible parameter handling
            # Try different parameter combinations to handle F5-TTS API version differences
            
            # Attempt 1: Use ref_file (older F5-TTS versions)
            infer_params = {
                "ref_file": voice_path,     # Reference audio file path (older F5-TTS versions)
                "gen_text": text,           # Text to generate
                "speed": speed,
                "remove_silence": True      # Remove silence for cleaner output
            }
            
            # Add reference text if available
            if ref_text:
                infer_params["ref_text"] = ref_text
                print(f"🎯 Using reference text for better voice cloning")
            
            # Try multiple inference approaches for API version compatibility
            inference_successful = False
            audio_data = None
            sample_rate = None
            
            # Attempt 1: ref_file parameter with infer method
            try:
                print(f"🔄 Attempting F5-TTS inference with 'ref_file' parameter...")
                audio_data, sample_rate, _ = current_model.infer(**infer_params)
                print(f"✅ F5-TTS inference successful with 'ref_file' - audio shape: {audio_data.shape}, sample_rate: {sample_rate}")
                inference_successful = True
            except Exception as ref_file_error:
                print(f"❌ F5-TTS inference failed with 'ref_file': {ref_file_error}")
                
                # Attempt 2: ref_audio parameter (newer F5-TTS versions)
                try:
                    print(f"🔄 Attempting F5-TTS inference with 'ref_audio' parameter...")
                    infer_params["ref_audio"] = infer_params.pop("ref_file")
                    audio_data, sample_rate, _ = current_model.infer(**infer_params)
                    print(f"✅ F5-TTS inference successful with 'ref_audio' - audio shape: {audio_data.shape}, sample_rate: {sample_rate}")
                    inference_successful = True
                except Exception as ref_audio_error:
                    print(f"❌ F5-TTS inference failed with 'ref_audio': {ref_audio_error}")
                    
                    # Attempt 3: Remove ref_text and try again
                    if "ref_text" in infer_params:
                        try:
                            print(f"🔄 Attempting F5-TTS inference without 'ref_text'...")
                            del infer_params["ref_text"]
                            audio_data, sample_rate, _ = current_model.infer(**infer_params)
                            print(f"✅ F5-TTS inference successful without ref_text - audio shape: {audio_data.shape}, sample_rate: {sample_rate}")
                            inference_successful = True
                        except Exception as no_ref_text_error:
                            print(f"❌ F5-TTS inference failed without ref_text: {no_ref_text_error}")
                            
                            # Attempt 4: Try generate method instead of infer (alternative API)
                            try:
                                print(f"🔄 Attempting F5-TTS with 'generate' method...")
                                # Restore ref_file for generate method
                                if "ref_audio" in infer_params:
                                    infer_params["ref_file"] = infer_params.pop("ref_audio")
                                result = current_model.generate(infer_params)
                                if isinstance(result, dict) and "wav" in result:
                                    audio_data = result["wav"]
                                    sample_rate = getattr(current_model, 'sample_rate', 24000)  # Default fallback
                                    print(f"✅ F5-TTS generate method successful - sample_rate: {sample_rate}")
                                    inference_successful = True
                                else:
                                    raise Exception("Generate method returned unexpected format")
                            except Exception as generate_error:
                                print(f"❌ F5-TTS generate method failed: {generate_error}")
                                # Re-raise the original error with context
                                raise Exception(f"All F5-TTS inference methods failed. Original errors - ref_file: {ref_file_error}, ref_audio: {ref_audio_error}, no_ref_text: {no_ref_text_error}, generate: {generate_error}")
            
            if not inference_successful:
                raise Exception("F5-TTS inference failed with all attempted methods")
            
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
            if jobs[job_id]["status"] != "COMPLETED":
                return {"error": f"Job is not complete. Status: {jobs[job_id]['status']}"}
            return jobs[job_id]["result"]
            
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
