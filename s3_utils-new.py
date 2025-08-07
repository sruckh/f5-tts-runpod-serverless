#!/usr/bin/env python3
"""
F5-TTS Engine for RunPod Serverless

Handles F5-TTS model loading, caching, and inference with warm loading
for 1-3 second inference performance.
"""

import os
import sys
import logging
import torch
import torchaudio
import time
from pathlib import Path
from typing import Optional, Union, Tuple

# Add container app path
sys.path.append('/app')

try:
    from setup_network_venv import (  # config.py
        F5TTS_MODELS_PATH, TEMP_PATH, DEFAULT_COMPUTE_TYPE
    )
except ImportError:
    F5TTS_MODELS_PATH = Path("/runpod-volume/f5tts/models/f5-tts")
    TEMP_PATH = Path("/runpod-volume/f5tts/temp")
    DEFAULT_COMPUTE_TYPE = "float16"

# Setup logging
logger = logging.getLogger(__name__)

class F5TTSEngine:
    """F5-TTS model engine with warm loading and caching."""
    
    def __init__(self, model_name: str = "F5TTS_Base", compute_type: str = DEFAULT_COMPUTE_TYPE):
        """
        Initialize F5-TTS engine.
        
        Args:
            model_name: Name of F5-TTS model to load
            compute_type: Compute type (float16, float32, int8)
        """
        self.model_name = model_name
        self.compute_type = compute_type
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Model components
        self.model = None
        self.vocoder = None
        self.tokenizer = None
        
        # Model cache paths
        self.model_dir = F5TTS_MODELS_PATH / model_name
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance tracking
        self.model_load_time = None
        self.last_inference_time = None
        
        logger.info(f"F5-TTS Engine initialized: {model_name} on {self.device}")
    
    def _setup_model_cache(self):
        """Setup model cache directory structure."""
        try:
            cache_dirs = [
                self.model_dir / "checkpoints",
                self.model_dir / "vocoder", 
                self.model_dir / "tokenizer"
            ]
            
            for cache_dir in cache_dirs:
                cache_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Model cache setup: {self.model_dir}")
            
        except Exception as e:
            logger.error(f"Failed to setup model cache: {e}")
            raise
    
    def load_model(self):
        """Load F5-TTS model with caching for warm loading."""
        try:
            if self.model is not None:
                logger.info("Model already loaded - using cached version")
                return
                
            start_time = time.time()
            logger.info(f"Loading F5-TTS model: {self.model_name}")
            
            # Setup cache directories
            self._setup_model_cache()
            
            # Import F5-TTS modules (only available after environment setup)
            try:
                from f5_tts.api import F5TTS
                from f5_tts.infer.utils_infer import (
                    load_model as load_f5tts_model,
                    load_vocoder
                )
            except ImportError as e:
                logger.error(f"F5-TTS import failed: {e}")
                raise RuntimeError("F5-TTS not available - check environment setup")
            
            # Load main model
            logger.info("Loading F5-TTS main model...")
            self.model = load_f5tts_model(
                model_name=self.model_name,
                device=self.device,
                cache_dir=str(self.model_dir / "checkpoints")
            )
            
            # Load vocoder
            logger.info("Loading vocoder...")  
            self.vocoder = load_vocoder(
                device=self.device,
                cache_dir=str(self.model_dir / "vocoder")
            )
            
            # Set compute type
            if self.compute_type == "float16" and self.device == "cuda":
                self.model = self.model.half()
                self.vocoder = self.vocoder.half()
                logger.info("Models converted to float16")
            
            # Model optimization for inference
            self.model.eval()
            self.vocoder.eval()
            
            with torch.no_grad():
                # Warm up models with dummy input
                logger.info("Warming up models...")
                dummy_text = "Hello world"
                dummy_audio = torch.randn(1, 24000).to(self.device)
                
                if self.compute_type == "float16":
                    dummy_audio = dummy_audio.half()
                
                # Run dummy inference to load CUDA kernels
                try:
                    _ = self.model.infer(
                        text=dummy_text,
                        ref_audio=dummy_audio,
                        ref_text="Reference audio",
                        gen_text=dummy_text
                    )
                except Exception as e:
                    logger.warning(f"Model warmup failed: {e}")
            
            self.model_load_time = time.time() - start_time
            logger.info(f"F5-TTS model loaded successfully in {self.model_load_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to load F5-TTS model: {e}")
            raise
    
    def process_reference_audio(self, audio_path: Union[str, Path]) -> Tuple[torch.Tensor, str]:
        """
        Process reference audio for F5-TTS.
        
        Args:
            audio_path: Path to reference audio file
            
        Returns:
            Tuple of (audio_tensor, reference_text)
        """
        try:
            audio_path = Path(audio_path)
            if not audio_path.exists():
                raise FileNotFoundError(f"Reference audio not found: {audio_path}")
            
            logger.info(f"Processing reference audio: {audio_path}")
            
            # Load audio
            audio, sample_rate = torchaudio.load(str(audio_path))
            
            # Resample to 24kHz if needed
            if sample_rate != 24000:
                resampler = torchaudio.transforms.Resample(sample_rate, 24000)
                audio = resampler(audio)
                logger.info(f"Resampled audio from {sample_rate}Hz to 24kHz")
            
            # Convert to mono if stereo
            if audio.shape[0] > 1:
                audio = torch.mean(audio, dim=0, keepdim=True)
                logger.info("Converted stereo audio to mono")
            
            # Move to device and set compute type
            audio = audio.to(self.device)
            if self.compute_type == "float16":
                audio = audio.half()
            
            # For now, use a default reference text
            # TODO: Implement ASR to get actual reference text
            reference_text = "This is a reference audio sample."
            
            logger.info("Reference audio processed successfully")
            return audio, reference_text
            
        except Exception as e:
            logger.error(f"Failed to process reference audio: {e}")
            raise
    
    def synthesize_speech(
        self, 
        text: str, 
        reference_audio_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Synthesize speech using F5-TTS.
        
        Args:
            text: Text to synthesize
            reference_audio_path: Path to reference voice audio
            output_path: Output audio file path (optional)
            
        Returns:
            Path to generated audio file
        """
        try:
            start_time = time.time()
            logger.info(f"Synthesizing speech for text length: {len(text)}")
            
            # Ensure model is loaded
            if self.model is None:
                self.load_model()
            
            # Process reference audio
            ref_audio, ref_text = self.process_reference_audio(reference_audio_path)
            
            # Generate output path if not provided
            if output_path is None:
                timestamp = int(time.time())
                output_path = TEMP_PATH / f"f5tts_output_{timestamp}.wav"
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate speech
            logger.info("Running F5-TTS inference...")
            
            with torch.no_grad():
                # Generate audio
                generated_audio = self.model.infer(
                    text=text,
                    ref_audio=ref_audio,
                    ref_text=ref_text,
                    gen_text=text
                )
                
                # Convert to CPU and save
                if isinstance(generated_audio, torch.Tensor):
                    generated_audio = generated_audio.cpu().float()
                    
                    # Save audio file
                    torchaudio.save(
                        str(output_path),
                        generated_audio,
                        24000  # 24kHz sample rate
                    )
                else:
                    raise RuntimeError(f"Unexpected model output type: {type(generated_audio)}")
            
            # Performance tracking
            inference_time = time.time() - start_time
            self.last_inference_time = inference_time
            
            logger.info(f"Speech synthesis completed in {inference_time:.2f}s")
            logger.info(f"Output saved to: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            raise
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "compute_type": self.compute_type,
            "device": self.device,
            "model_loaded": self.model is not None,
            "model_load_time": self.model_load_time,
            "last_inference_time": self.last_inference_time,
            "cuda_available": torch.cuda.is_available(),
            "cuda_memory": torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else None
        }
    
    def cleanup(self):
        """Clean up model and free memory."""
        try:
            if self.model is not None:
                del self.model
                self.model = None
                
            if self.vocoder is not None:
                del self.vocoder
                self.vocoder = None
                
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            logger.info("F5-TTS engine cleaned up")
            
        except Exception as e:
            logger.error(f"Failed to cleanup F5-TTS engine: {e}")

# Global engine instance for warm loading
_f5tts_engine = None

def get_f5tts_engine() -> F5TTSEngine:
    """Get global F5-TTS engine instance."""
    global _f5tts_engine
    if _f5tts_engine is None:
        _f5tts_engine = F5TTSEngine()
    return _f5tts_engine

def process_tts(text: str, reference_audio_path: Union[str, Path]) -> Path:
    """
    Convenience function for TTS processing.
    
    Args:
        text: Text to synthesize  
        reference_audio_path: Path to reference audio
        
    Returns:
        Path to generated audio file
    """
    engine = get_f5tts_engine()
    return engine.synthesize_speech(text, reference_audio_path)

# Test function
if __name__ == "__main__":
    """Test F5-TTS engine."""
    try:
        engine = F5TTSEngine()
        logger.info("F5-TTS engine test passed")
        
        # Print model info
        info = engine.get_model_info()
        for key, value in info.items():
            logger.info(f"{key}: {value}")
            
    except Exception as e:
        logger.error(f"F5-TTS engine test failed: {e}")
        sys.exit(1)#!/usr/bin/env python3
"""
F5-TTS Engine for RunPod Serverless

Handles F5-TTS model loading, caching, and inference with warm loading
for 1-3 second inference performance.
"""

import os
import sys
import logging
import torch
import torchaudio
import time
from pathlib import Path
from typing import Optional, Union, Tuple

# Add container app path
sys.path.append('/app')

try:
    from setup_network_venv import (  # config.py
        F5TTS_MODELS_PATH, TEMP_PATH, DEFAULT_COMPUTE_TYPE
    )
except ImportError:
    F5TTS_MODELS_PATH = Path("/runpod-volume/f5tts/models/f5-tts")
    TEMP_PATH = Path("/runpod-volume/f5tts/temp")
    DEFAULT_COMPUTE_TYPE = "float16"

# Setup logging
logger = logging.getLogger(__name__)

class F5TTSEngine:
    """F5-TTS model engine with warm loading and caching."""
    
    def __init__(self, model_name: str = "F5TTS_Base", compute_type: str = DEFAULT_COMPUTE_TYPE):
        """
        Initialize F5-TTS engine.
        
        Args:
            model_name: Name of F5-TTS model to load
            compute_type: Compute type (float16, float32, int8)
        """
        self.model_name = model_name
        self.compute_type = compute_type
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Model components
        self.model = None
        self.vocoder = None
        self.tokenizer = None
        
        # Model cache paths
        self.model_dir = F5TTS_MODELS_PATH / model_name
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance tracking
        self.model_load_time = None
        self.last_inference_time = None
        
        logger.info(f"F5-TTS Engine initialized: {model_name} on {self.device}")
    
    def _setup_model_cache(self):
        """Setup model cache directory structure."""
        try:
            cache_dirs = [
                self.model_dir / "checkpoints",
                self.model_dir / "vocoder", 
                self.model_dir / "tokenizer"
            ]
            
            for cache_dir in cache_dirs:
                cache_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Model cache setup: {self.model_dir}")
            
        except Exception as e:
            logger.error(f"Failed to setup model cache: {e}")
            raise
    
    def load_model(self):
        """Load F5-TTS model with caching for warm loading."""
        try:
            if self.model is not None:
                logger.info("Model already loaded - using cached version")
                return
                
            start_time = time.time()
            logger.info(f"Loading F5-TTS model: {self.model_name}")
            
            # Setup cache directories
            self._setup_model_cache()
            
            # Import F5-TTS modules (only available after environment setup)
            try:
                from f5_tts.api import F5TTS
                from f5_tts.infer.utils_infer import (
                    load_model as load_f5tts_model,
                    load_vocoder
                )
            except ImportError as e:
                logger.error(f"F5-TTS import failed: {e}")
                raise RuntimeError("F5-TTS not available - check environment setup")
            
            # Load main model
            logger.info("Loading F5-TTS main model...")
            self.model = load_f5tts_model(
                model_name=self.model_name,
                device=self.device,
                cache_dir=str(self.model_dir / "checkpoints")
            )
            
            # Load vocoder
            logger.info("Loading vocoder...")  
            self.vocoder = load_vocoder(
                device=self.device,
                cache_dir=str(self.model_dir / "vocoder")
            )
            
            # Set compute type
            if self.compute_type == "float16" and self.device == "cuda":
                self.model = self.model.half()
                self.vocoder = self.vocoder.half()
                logger.info("Models converted to float16")
            
            # Model optimization for inference
            self.model.eval()
            self.vocoder.eval()
            
            with torch.no_grad():
                # Warm up models with dummy input
                logger.info("Warming up models...")
                dummy_text = "Hello world"
                dummy_audio = torch.randn(1, 24000).to(self.device)
                
                if self.compute_type == "float16":
                    dummy_audio = dummy_audio.half()
                
                # Run dummy inference to load CUDA kernels
                try:
                    _ = self.model.infer(
                        text=dummy_text,
                        ref_audio=dummy_audio,
                        ref_text="Reference audio",
                        gen_text=dummy_text
                    )
                except Exception as e:
                    logger.warning(f"Model warmup failed: {e}")
            
            self.model_load_time = time.time() - start_time
            logger.info(f"F5-TTS model loaded successfully in {self.model_load_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to load F5-TTS model: {e}")
            raise
    
    def process_reference_audio(self, audio_path: Union[str, Path]) -> Tuple[torch.Tensor, str]:
        """
        Process reference audio for F5-TTS.
        
        Args:
            audio_path: Path to reference audio file
            
        Returns:
            Tuple of (audio_tensor, reference_text)
        """
        try:
            audio_path = Path(audio_path)
            if not audio_path.exists():
                raise FileNotFoundError(f"Reference audio not found: {audio_path}")
            
            logger.info(f"Processing reference audio: {audio_path}")
            
            # Load audio
            audio, sample_rate = torchaudio.load(str(audio_path))
            
            # Resample to 24kHz if needed
            if sample_rate != 24000:
                resampler = torchaudio.transforms.Resample(sample_rate, 24000)
                audio = resampler(audio)
                logger.info(f"Resampled audio from {sample_rate}Hz to 24kHz")
            
            # Convert to mono if stereo
            if audio.shape[0] > 1:
                audio = torch.mean(audio, dim=0, keepdim=True)
                logger.info("Converted stereo audio to mono")
            
            # Move to device and set compute type
            audio = audio.to(self.device)
            if self.compute_type == "float16":
                audio = audio.half()
            
            # For now, use a default reference text
            # TODO: Implement ASR to get actual reference text
            reference_text = "This is a reference audio sample."
            
            logger.info("Reference audio processed successfully")
            return audio, reference_text
            
        except Exception as e:
            logger.error(f"Failed to process reference audio: {e}")
            raise
    
    def synthesize_speech(
        self, 
        text: str, 
        reference_audio_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Synthesize speech using F5-TTS.
        
        Args:
            text: Text to synthesize
            reference_audio_path: Path to reference voice audio
            output_path: Output audio file path (optional)
            
        Returns:
            Path to generated audio file
        """
        try:
            start_time = time.time()
            logger.info(f"Synthesizing speech for text length: {len(text)}")
            
            # Ensure model is loaded
            if self.model is None:
                self.load_model()
            
            # Process reference audio
            ref_audio, ref_text = self.process_reference_audio(reference_audio_path)
            
            # Generate output path if not provided
            if output_path is None:
                timestamp = int(time.time())
                output_path = TEMP_PATH / f"f5tts_output_{timestamp}.wav"
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate speech
            logger.info("Running F5-TTS inference...")
            
            with torch.no_grad():
                # Generate audio
                generated_audio = self.model.infer(
                    text=text,
                    ref_audio=ref_audio,
                    ref_text=ref_text,
                    gen_text=text
                )
                
                # Convert to CPU and save
                if isinstance(generated_audio, torch.Tensor):
                    generated_audio = generated_audio.cpu().float()
                    
                    # Save audio file
                    torchaudio.save(
                        str(output_path),
                        generated_audio,
                        24000  # 24kHz sample rate
                    )
                else:
                    raise RuntimeError(f"Unexpected model output type: {type(generated_audio)}")
            
            # Performance tracking
            inference_time = time.time() - start_time
            self.last_inference_time = inference_time
            
            logger.info(f"Speech synthesis completed in {inference_time:.2f}s")
            logger.info(f"Output saved to: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            raise
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "compute_type": self.compute_type,
            "device": self.device,
            "model_loaded": self.model is not None,
            "model_load_time": self.model_load_time,
            "last_inference_time": self.last_inference_time,
            "cuda_available": torch.cuda.is_available(),
            "cuda_memory": torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else None
        }
    
    def cleanup(self):
        """Clean up model and free memory."""
        try:
            if self.model is not None:
                del self.model
                self.model = None
                
            if self.vocoder is not None:
                del self.vocoder
                self.vocoder = None
                
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            logger.info("F5-TTS engine cleaned up")
            
        except Exception as e:
            logger.error(f"Failed to cleanup F5-TTS engine: {e}")

# Global engine instance for warm loading
_f5tts_engine = None

def get_f5tts_engine() -> F5TTSEngine:
    """Get global F5-TTS engine instance."""
    global _f5tts_engine
    if _f5tts_engine is None:
        _f5tts_engine = F5TTSEngine()
    return _f5tts_engine

def process_tts(text: str, reference_audio_path: Union[str, Path]) -> Path:
    """
    Convenience function for TTS processing.
    
    Args:
        text: Text to synthesize  
        reference_audio_path: Path to reference audio
        
    Returns:
        Path to generated audio file
    """
    engine = get_f5tts_engine()
    return engine.synthesize_speech(text, reference_audio_path)

# Test function
if __name__ == "__main__":
    """Test F5-TTS engine."""
    try:
        engine = F5TTSEngine()
        logger.info("F5-TTS engine test passed")
        
        # Print model info
        info = engine.get_model_info()
        for key, value in info.items():
            logger.info(f"{key}: {value}")
            
    except Exception as e:
        logger.error(f"F5-TTS engine test failed: {e}")
        sys.exit(1)