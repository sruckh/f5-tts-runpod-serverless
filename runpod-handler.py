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
    """Loads the F5-TTS model."""
    global model
    try:
        from f5_tts.api import F5TTS
        model = F5TTS(model_type="F5-TTS", ckpt_file="", vocab_file="")
        print(f"F5-TTS model loaded on {device}")
    except Exception as e:
        print(f"Error loading F5-TTS model: {e}")
        model = None

# --- Helper Functions ---
def process_tts_job(job_id, text, speed, return_word_timings, local_voice):
    try:
        jobs[job_id]["status"] = "PROCESSING"

        voice_path = None
        if local_voice:
            voice_path = f"/tmp/{local_voice}"
            download_from_s3(f"voices/{local_voice}", voice_path)

        words = text.split()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            audio_data = model.infer(
                text=text,
                ref_audio_path=voice_path,
                speed=speed
            )
            sf.write(temp_audio.name, audio_data, 22050)

            word_timings = []
            total_duration = len(audio_data) / 22050

            if return_word_timings:
                words_per_second = len(words) / total_duration
                current_time = 0.0
                for word in words:
                    word_duration = max(0.2, len(word) * 0.08 / speed)
                    word_timings.append(WordTiming(
                        word=word,
                        start_time=current_time,
                        end_time=current_time + word_duration
                    ))
                    current_time += word_duration + 0.05

            audio_url = upload_to_s3(temp_audio.name, f"output/{job_id}.wav")
            os.unlink(temp_audio.name)

            if voice_path:
                os.unlink(voice_path)

            jobs[job_id]["status"] = "COMPLETED"
            jobs[job_id]["result"] = {
                "audio_url": audio_url,
                "word_timings": [wt.dict() for wt in word_timings],
                "duration": total_duration
            }

    except Exception as e:
        jobs[job_id]["status"] = "ERROR"
        jobs[job_id]["error"] = str(e)

# --- RunPod Handler ---
def handler(job):
    """
    RunPod serverless handler for F5-TTS.
    """
    if not model:
        load_model()
        if not model:
            return {"error": "TTS model not loaded"}

    job_input = job.get('input', {})
    endpoint = job_input.get("endpoint")

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

if __name__ == "__main__":
    load_model()
    runpod.serverless.start({"handler": handler})
