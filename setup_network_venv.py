#!/usr/bin/env python3
"""
Network Volume Virtual Environment Setup
Creates and manages Python virtual environment on /runpod-volume
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_package_installed(package_name, venv_python):
    """Check if a package is already installed in the virtual environment."""
    try:
        cmd = [str(venv_python), "-c", f"import {package_name}"]
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False

def setup_network_volume_venv():
    """Create and configure virtual environment on network volume."""
    
    # Network volume paths
    volume_root = Path("/runpod-volume")
    venv_path = volume_root / "venv"
    models_path = volume_root / "models" 
    cache_path = volume_root / "cache"
    
    print(f"🔧 Setting up network volume virtual environment...")
    print(f"   Volume root: {volume_root}")
    print(f"   Venv path: {venv_path}")
    print(f"   Models path: {models_path}")
    
    # Check network volume availability
    if not volume_root.exists():
        print(f"❌ Network volume not available at {volume_root}")
        return False
        
    # Check available space
    statvfs = os.statvfs(str(volume_root))
    free_space_gb = (statvfs.f_frsize * statvfs.f_available) / (1024**3)
    print(f"📊 Network volume free space: {free_space_gb:.1f}GB")
    
    if free_space_gb < 10:
        print(f"⚠️ Low disk space on network volume: {free_space_gb:.1f}GB")
        return False
    
    # Create directory structure
    for path in [models_path, cache_path]:
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {path}")
    
    # Create virtual environment if it doesn't exist
    if not venv_path.exists():
        print(f"🏗️ Creating virtual environment at {venv_path}")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])
            print(f"✅ Virtual environment created successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
    else:
        print(f"✅ Virtual environment already exists at {venv_path}")
    
    # Get venv python and pip paths
    venv_python = venv_path / "bin" / "python"
    venv_pip = venv_path / "bin" / "pip"
    
    if not venv_python.exists():
        print(f"❌ Virtual environment Python not found: {venv_python}")
        return False
        
    print(f"🐍 Using venv Python: {venv_python}")
    print(f"📦 Using venv pip: {venv_pip}")
    
    # Set environment variables for this session
    os.environ['VIRTUAL_ENV'] = str(venv_path)
    os.environ['PATH'] = f"{venv_path / 'bin'}:{os.environ.get('PATH', '')}"
    
    # Set cache directories to network volume
    os.environ['HF_HOME'] = str(models_path)
    os.environ['TRANSFORMERS_CACHE'] = str(models_path)
    os.environ['HF_HUB_CACHE'] = str(models_path / 'hub')
    os.environ['TORCH_HOME'] = str(models_path / 'torch')
    os.environ['PIP_CACHE_DIR'] = str(cache_path / 'pip')
    
    # Create cache subdirectories
    for cache_dir in ['hub', 'torch']:
        (models_path / cache_dir).mkdir(exist_ok=True)
    (cache_path / 'pip').mkdir(parents=True, exist_ok=True)
    
    print(f"✅ Environment variables configured")
    
    # Install packages in order of importance and size
    package_installs = [
        # Core dependencies (small, essential)
        ("runpod", "runpod"),
        ("boto3", "boto3"), 
        ("requests", "requests"),
        ("librosa", "librosa"),
        ("soundfile", "soundfile"),
        ("ass", "ass"),
        
        # PyTorch (large but essential, install first to establish CUDA)
        ("torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121", "torch"),
        
        # Transformers (medium size, essential for F5-TTS)
        ("transformers>=4.48.1", "transformers"),
        
        # F5-TTS itself
        ("f5-tts", "f5_tts"),
        
        # Optional but important (install these if space allows)
        ("google-cloud-speech", "google.cloud.speech"),
        ("whisperx", "whisperx"),
        
        # Flash attention (largest, most problematic - install last)
        ("flash-attn --no-build-isolation", "flash_attn"),
    ]
    
    for install_cmd, import_name in package_installs:
        # Check if already installed
        if check_package_installed(import_name.split('.')[0], venv_python):
            print(f"✅ {import_name} already installed")
            continue
            
        # Check disk space before installation
        statvfs = os.statvfs(str(volume_root))
        free_space_gb = (statvfs.f_frsize * statvfs.f_available) / (1024**3)
        
        if free_space_gb < 2:  # Less than 2GB free
            print(f"⚠️ Skipping {import_name} - insufficient space: {free_space_gb:.1f}GB")
            continue
            
        try:
            print(f"📦 Installing: {install_cmd}")
            # Parse install command properly
            if "--" in install_cmd:
                # Handle commands with special flags like "torch torchvision torchaudio --index-url ..."
                cmd = [str(venv_pip), "install", "--no-cache-dir"] + install_cmd.split()
            else:
                # Handle simple package names
                cmd = [str(venv_pip), "install", "--no-cache-dir", install_cmd]
            subprocess.check_call(cmd, cwd=str(volume_root))
            print(f"✅ Installed: {import_name}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to install {import_name}: {e}")
            # Continue with other packages - don't fail completely
    
    print(f"🎉 Network volume virtual environment setup complete!")
    print(f"📊 Final disk usage:")
    
    # Report disk usage
    statvfs = os.statvfs(str(volume_root))
    free_space_gb = (statvfs.f_frsize * statvfs.f_available) / (1024**3)
    used_space_gb = (statvfs.f_frsize * (statvfs.f_blocks - statvfs.f_available)) / (1024**3)
    print(f"   Used: {used_space_gb:.1f}GB")
    print(f"   Free: {free_space_gb:.1f}GB") 
    
    return True

if __name__ == "__main__":
    try:
        success = setup_network_volume_venv()
        if success:
            print("✅ Network volume virtual environment setup complete!")
            print("🎯 Container ready for RunPod serverless execution")
            sys.exit(0)
        else:
            print("❌ Network volume virtual environment setup failed!")
            print("💡 Check RunPod network volume configuration and available space")
            sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error during setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)