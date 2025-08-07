#!/usr/bin/env python3
"""
Setup Environment for F5-TTS RunPod Serverless
Network Volume Environment Setup (Layer 2)

This script handles the first-time setup of the network volume environment:
1. Create virtual environment
2. Install PyTorch with CUDA support
3. Install F5-TTS and WhisperX
4. Setup model directories and caching
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
import shutil
import time

# Import configuration constants
sys.path.append('/app')
from setup_network_venv import (  # This is our config.py
    NETWORK_VOLUME_PATH, VENV_PATH, MODELS_PATH, TEMP_PATH, 
    LOGS_PATH, CACHE_PATH, PYTORCH_VERSION, PYTORCH_INDEX_URL,
    FLASH_ATTN_WHEEL, RUNTIME_REQUIREMENTS
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(cmd: str, cwd: Path = None, timeout: int = 3600) -> bool:
    """Run shell command with proper error handling."""
    try:
        logger.info(f"Running: {cmd}")
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=True, 
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        if result.stdout:
            logger.info(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {cmd}")
        logger.error(f"Return code: {e.returncode}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd}")
        return False

def create_directory_structure():
    """Create network volume directory structure."""
    try:
        directories = [
            NETWORK_VOLUME_PATH,
            MODELS_PATH,
            MODELS_PATH / "f5-tts",
            MODELS_PATH / "whisperx",
            TEMP_PATH,
            LOGS_PATH,
            CACHE_PATH
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create directory structure: {e}")
        return False

def create_virtual_environment():
    """Create Python virtual environment."""
    try:
        logger.info("Creating virtual environment...")
        
        # Remove existing venv if it exists but is broken
        if VENV_PATH.exists():
            logger.warning("Removing existing virtual environment")
            shutil.rmtree(VENV_PATH)
        
        # Create new virtual environment
        cmd = f"python3 -m venv {VENV_PATH}"
        if not run_command(cmd):
            return False
            
        logger.info("Virtual environment created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create virtual environment: {e}")
        return False

def get_venv_python():
    """Get path to virtual environment Python executable."""
    return VENV_PATH / "bin" / "python"

def get_venv_pip():
    """Get path to virtual environment pip executable."""
    return VENV_PATH / "bin" / "pip"

def install_pytorch():
    """Install PyTorch with CUDA support."""
    try:
        logger.info("Installing PyTorch with CUDA support...")
        
        pip_cmd = str(get_venv_pip())
        pytorch_cmd = f"{pip_cmd} install {PYTORCH_VERSION} --index-url {PYTORCH_INDEX_URL}"
        
        if not run_command(pytorch_cmd, timeout=1800):  # 30 minute timeout
            return False
            
        logger.info("PyTorch installed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to install PyTorch: {e}")
        return False

def install_flash_attention():
    """Install Flash Attention wheel."""
    try:
        logger.info("Installing Flash Attention...")
        
        pip_cmd = str(get_venv_pip())
        flash_cmd = f"{pip_cmd} install {FLASH_ATTN_WHEEL}"
        
        if not run_command(flash_cmd, timeout=600):  # 10 minute timeout
            return False
            
        logger.info("Flash Attention installed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to install Flash Attention: {e}")
        return False

def install_runtime_requirements():
    """Install all runtime requirements."""
    try:
        logger.info("Installing runtime requirements...")
        
        pip_cmd = str(get_venv_pip())
        
        for requirement in RUNTIME_REQUIREMENTS:
            if requirement.startswith(PYTORCH_VERSION):
                # Skip PyTorch - already installed
                continue
            if requirement == FLASH_ATTN_WHEEL:
                # Skip flash attention - already installed
                continue
                
            cmd = f"{pip_cmd} install {requirement}"
            if not run_command(cmd, timeout=1200):  # 20 minute timeout per package
                logger.error(f"Failed to install: {requirement}")
                return False
            
            # Small delay between installations
            time.sleep(2)
        
        logger.info("Runtime requirements installed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to install runtime requirements: {e}")
        return False

def verify_installation():
    """Verify that key packages are installed correctly."""
    try:
        logger.info("Verifying installation...")
        
        python_cmd = str(get_venv_python())
        
        # Test PyTorch with CUDA
        pytorch_test = f"{python_cmd} -c \"import torch; print(f'PyTorch: {{torch.__version__}}'); print(f'CUDA available: {{torch.cuda.is_available()}}')\""
        if not run_command(pytorch_test):
            return False
        
        # Test WhisperX
        whisperx_test = f"{python_cmd} -c \"import whisperx; print('WhisperX imported successfully')\""
        if not run_command(whisperx_test):
            logger.warning("WhisperX import failed - may need additional setup")
            
        # Test ASS library
        ass_test = f"{python_cmd} -c \"import ass; print('ASS library imported successfully')\""
        if not run_command(ass_test):
            logger.warning("ASS library import failed")
        
        logger.info("Installation verification completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify installation: {e}")
        return False

def setup_model_cache():
    """Setup model cache directories with proper permissions."""
    try:
        logger.info("Setting up model cache...")
        
        # Create model subdirectories
        model_dirs = [
            MODELS_PATH / "f5-tts" / "checkpoints",
            MODELS_PATH / "whisperx" / "models",
            MODELS_PATH / "whisperx" / "align_models"
        ]
        
        for model_dir in model_dirs:
            model_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created model cache: {model_dir}")
        
        logger.info("Model cache setup completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup model cache: {e}")
        return False

def setup_network_volume_environment():
    """
    Main function to setup complete network volume environment.
    This is called during cold start (first request).
    """
    try:
        logger.info("=== F5-TTS Network Volume Environment Setup ===")
        start_time = time.time()
        
        # Step 1: Create directory structure
        logger.info("Step 1: Creating directory structure...")
        if not create_directory_structure():
            raise RuntimeError("Failed to create directory structure")
        
        # Step 2: Create virtual environment
        logger.info("Step 2: Creating virtual environment...")
        if not create_virtual_environment():
            raise RuntimeError("Failed to create virtual environment")
        
        # Step 3: Install PyTorch with CUDA
        logger.info("Step 3: Installing PyTorch with CUDA...")
        if not install_pytorch():
            raise RuntimeError("Failed to install PyTorch")
        
        # Step 4: Install Flash Attention
        logger.info("Step 4: Installing Flash Attention...")
        if not install_flash_attention():
            raise RuntimeError("Failed to install Flash Attention")
        
        # Step 5: Install runtime requirements
        logger.info("Step 5: Installing runtime requirements...")
        if not install_runtime_requirements():
            raise RuntimeError("Failed to install runtime requirements")
        
        # Step 6: Setup model cache
        logger.info("Step 6: Setting up model cache...")
        if not setup_model_cache():
            raise RuntimeError("Failed to setup model cache")
        
        # Step 7: Verify installation
        logger.info("Step 7: Verifying installation...")
        if not verify_installation():
            logger.warning("Installation verification had warnings but continuing...")
        
        # Calculate setup time
        setup_time = time.time() - start_time
        logger.info(f"=== Setup completed successfully in {setup_time:.1f} seconds ===")
        
        return True
        
    except Exception as e:
        logger.error(f"Network volume setup failed: {e}")
        raise

if __name__ == "__main__":
    """Run setup environment directly for testing."""
    try:
        success = setup_network_volume_environment()
        if success:
            print("Setup completed successfully!")
            sys.exit(0)
        else:
            print("Setup failed!")
            sys.exit(1)
    except Exception as e:
        print(f"Setup error: {e}")
        sys.exit(1)#!/usr/bin/env python3
"""
Setup Environment for F5-TTS RunPod Serverless
Network Volume Environment Setup (Layer 2)

This script handles the first-time setup of the network volume environment:
1. Create virtual environment
2. Install PyTorch with CUDA support
3. Install F5-TTS and WhisperX
4. Setup model directories and caching
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
import shutil
import time

# Import configuration constants
sys.path.append('/app')
from setup_network_venv import (  # This is our config.py
    NETWORK_VOLUME_PATH, VENV_PATH, MODELS_PATH, TEMP_PATH, 
    LOGS_PATH, CACHE_PATH, PYTORCH_VERSION, PYTORCH_INDEX_URL,
    FLASH_ATTN_WHEEL, RUNTIME_REQUIREMENTS
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(cmd: str, cwd: Path = None, timeout: int = 3600) -> bool:
    """Run shell command with proper error handling."""
    try:
        logger.info(f"Running: {cmd}")
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=True, 
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        if result.stdout:
            logger.info(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {cmd}")
        logger.error(f"Return code: {e.returncode}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd}")
        return False

def create_directory_structure():
    """Create network volume directory structure."""
    try:
        directories = [
            NETWORK_VOLUME_PATH,
            MODELS_PATH,
            MODELS_PATH / "f5-tts",
            MODELS_PATH / "whisperx",
            TEMP_PATH,
            LOGS_PATH,
            CACHE_PATH
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create directory structure: {e}")
        return False

def create_virtual_environment():
    """Create Python virtual environment."""
    try:
        logger.info("Creating virtual environment...")
        
        # Remove existing venv if it exists but is broken
        if VENV_PATH.exists():
            logger.warning("Removing existing virtual environment")
            shutil.rmtree(VENV_PATH)
        
        # Create new virtual environment
        cmd = f"python3 -m venv {VENV_PATH}"
        if not run_command(cmd):
            return False
            
        logger.info("Virtual environment created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create virtual environment: {e}")
        return False

def get_venv_python():
    """Get path to virtual environment Python executable."""
    return VENV_PATH / "bin" / "python"

def get_venv_pip():
    """Get path to virtual environment pip executable."""
    return VENV_PATH / "bin" / "pip"

def install_pytorch():
    """Install PyTorch with CUDA support."""
    try:
        logger.info("Installing PyTorch with CUDA support...")
        
        pip_cmd = str(get_venv_pip())
        pytorch_cmd = f"{pip_cmd} install {PYTORCH_VERSION} --index-url {PYTORCH_INDEX_URL}"
        
        if not run_command(pytorch_cmd, timeout=1800):  # 30 minute timeout
            return False
            
        logger.info("PyTorch installed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to install PyTorch: {e}")
        return False

def install_flash_attention():
    """Install Flash Attention wheel."""
    try:
        logger.info("Installing Flash Attention...")
        
        pip_cmd = str(get_venv_pip())
        flash_cmd = f"{pip_cmd} install {FLASH_ATTN_WHEEL}"
        
        if not run_command(flash_cmd, timeout=600):  # 10 minute timeout
            return False
            
        logger.info("Flash Attention installed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to install Flash Attention: {e}")
        return False

def install_runtime_requirements():
    """Install all runtime requirements."""
    try:
        logger.info("Installing runtime requirements...")
        
        pip_cmd = str(get_venv_pip())
        
        for requirement in RUNTIME_REQUIREMENTS:
            if requirement.startswith(PYTORCH_VERSION):
                # Skip PyTorch - already installed
                continue
            if requirement == FLASH_ATTN_WHEEL:
                # Skip flash attention - already installed
                continue
                
            cmd = f"{pip_cmd} install {requirement}"
            if not run_command(cmd, timeout=1200):  # 20 minute timeout per package
                logger.error(f"Failed to install: {requirement}")
                return False
            
            # Small delay between installations
            time.sleep(2)
        
        logger.info("Runtime requirements installed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to install runtime requirements: {e}")
        return False

def verify_installation():
    """Verify that key packages are installed correctly."""
    try:
        logger.info("Verifying installation...")
        
        python_cmd = str(get_venv_python())
        
        # Test PyTorch with CUDA
        pytorch_test = f"{python_cmd} -c \"import torch; print(f'PyTorch: {{torch.__version__}}'); print(f'CUDA available: {{torch.cuda.is_available()}}')\""
        if not run_command(pytorch_test):
            return False
        
        # Test WhisperX
        whisperx_test = f"{python_cmd} -c \"import whisperx; print('WhisperX imported successfully')\""
        if not run_command(whisperx_test):
            logger.warning("WhisperX import failed - may need additional setup")
            
        # Test ASS library
        ass_test = f"{python_cmd} -c \"import ass; print('ASS library imported successfully')\""
        if not run_command(ass_test):
            logger.warning("ASS library import failed")
        
        logger.info("Installation verification completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify installation: {e}")
        return False

def setup_model_cache():
    """Setup model cache directories with proper permissions."""
    try:
        logger.info("Setting up model cache...")
        
        # Create model subdirectories
        model_dirs = [
            MODELS_PATH / "f5-tts" / "checkpoints",
            MODELS_PATH / "whisperx" / "models",
            MODELS_PATH / "whisperx" / "align_models"
        ]
        
        for model_dir in model_dirs:
            model_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created model cache: {model_dir}")
        
        logger.info("Model cache setup completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup model cache: {e}")
        return False

def setup_network_volume_environment():
    """
    Main function to setup complete network volume environment.
    This is called during cold start (first request).
    """
    try:
        logger.info("=== F5-TTS Network Volume Environment Setup ===")
        start_time = time.time()
        
        # Step 1: Create directory structure
        logger.info("Step 1: Creating directory structure...")
        if not create_directory_structure():
            raise RuntimeError("Failed to create directory structure")
        
        # Step 2: Create virtual environment
        logger.info("Step 2: Creating virtual environment...")
        if not create_virtual_environment():
            raise RuntimeError("Failed to create virtual environment")
        
        # Step 3: Install PyTorch with CUDA
        logger.info("Step 3: Installing PyTorch with CUDA...")
        if not install_pytorch():
            raise RuntimeError("Failed to install PyTorch")
        
        # Step 4: Install Flash Attention
        logger.info("Step 4: Installing Flash Attention...")
        if not install_flash_attention():
            raise RuntimeError("Failed to install Flash Attention")
        
        # Step 5: Install runtime requirements
        logger.info("Step 5: Installing runtime requirements...")
        if not install_runtime_requirements():
            raise RuntimeError("Failed to install runtime requirements")
        
        # Step 6: Setup model cache
        logger.info("Step 6: Setting up model cache...")
        if not setup_model_cache():
            raise RuntimeError("Failed to setup model cache")
        
        # Step 7: Verify installation
        logger.info("Step 7: Verifying installation...")
        if not verify_installation():
            logger.warning("Installation verification had warnings but continuing...")
        
        # Calculate setup time
        setup_time = time.time() - start_time
        logger.info(f"=== Setup completed successfully in {setup_time:.1f} seconds ===")
        
        return True
        
    except Exception as e:
        logger.error(f"Network volume setup failed: {e}")
        raise

if __name__ == "__main__":
    """Run setup environment directly for testing."""
    try:
        success = setup_network_volume_environment()
        if success:
            print("Setup completed successfully!")
            sys.exit(0)
        else:
            print("Setup failed!")
            sys.exit(1)
    except Exception as e:
        print(f"Setup error: {e}")
        sys.exit(1)