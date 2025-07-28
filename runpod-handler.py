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

# --- Pydantic Models ---
class WordTiming(BaseModel):
    word: str
    start_time: float
    end_time: float

class TTSResponse(BaseModel):
    audio_data: str  # Base64 encoded
    word_timings: List[WordTiming]
    duration: float

# --- Model Loading ---
model = None
device = "cuda" if torch.cuda.is_available() else "cpu"

def load_model():
    """Loads the F5-TTS model."""
    global model
    try:
        from f5_tts.api import F5TTS
        # Note: You might need to adjust ckpt_file and vocab_file paths
        model = F5TTS(model_type="F5-TTS", ckpt_file="", vocab_file="")
        print(f"F5-TTS model loaded on {device}")
    except Exception as e:
        print(f"Error loading F5-TTS model: {e}")
        model = None

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
    text = job_input.get('text')
    speed = job_input.get('speed', 1.0)
    return_word_timings = job_input.get('return_word_timings', True)

    if not text:
        return {"error": "Text input is required."}

    try:
        # Split text into words for timing calculation
        words = text.split()

        # Generate audio using F5-TTS
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            # F5-TTS generation (simplified - adapt based on actual F5-TTS API)
            audio_data = model.infer(
                text=text,
                ref_audio_path=None,  # Use default voice
                speed=speed
            )

            # Save audio
            sf.write(temp_audio.name, audio_data, 22050)

            # Calculate word timings (simplified algorithm)
            word_timings = []
            total_duration = len(audio_data) / 22050  # Sample rate

            if return_word_timings:
                # Estimate word timing based on text length and audio duration
                words_per_second = len(words) / total_duration
                current_time = 0.0

                for word in words:
                    # Estimate word duration based on character count
                    word_duration = max(0.2, len(word) * 0.08 / speed)

                    word_timings.append(WordTiming(
                        word=word,
                        start_time=current_time,
                        end_time=current_time + word_duration
                    ))

                    current_time += word_duration + 0.05  # Small pause between words

            # Encode audio as base64
            with open(temp_audio.name, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode()

            # Cleanup
            os.unlink(temp_audio.name)

            response = TTSResponse(
                audio_data=audio_base64,
                word_timings=[wt.dict() for wt in word_timings],
                duration=total_duration
            )
            return response.dict()

    except Exception as e:
        return {"error": f"TTS generation failed: {str(e)}"}

if __name__ == "__main__":
    load_model()
    runpod.serverless.start({"handler": handler})