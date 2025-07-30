#!/usr/bin/env python3
"""
Model cache initialization script for F5-TTS RunPod deployment.
Ensures models are properly cached in persistent storage.
"""

import os
import sys
import shutil
import subprocess
import torch
from pathlib import Path

def ensure_cache_directories():
    """Ensure all cache directories exist with proper permissions."""
    cache_dirs = [
        "/runpod-volume/models",
        "/runpod-volume/models/hub", 
        "/runpod-volume/models/torch",
        "/runpod-volume/models/f5-tts"
    ]
    
    for cache_dir in cache_dirs:
        try:
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
            print(f"✅ Cache directory ready: {cache_dir}")
        except Exception as e:
            print(f"⚠️  Warning: Could not create {cache_dir}: {e}")
            # Fallback to local directory
            fallback_dir = cache_dir.replace("/runpod-volume", "/app")
            Path(fallback_dir).mkdir(parents=True, exist_ok=True)
            print(f"📁 Using fallback: {fallback_dir}")

def migrate_existing_models():
    """Migrate any existing models from local to persistent storage."""
    local_models = "/app/models"
    persistent_models = "/runpod-volume/models"
    
    if os.path.exists(local_models) and os.path.exists(persistent_models):
        try:
            # Check if there are models to migrate
            local_files = list(Path(local_models).rglob("*"))
            if local_files:
                print(f"🔄 Migrating {len(local_files)} model files to persistent storage...")
                for file_path in local_files:
                    if file_path.is_file():
                        relative_path = file_path.relative_to(local_models)
                        dest_path = Path(persistent_models) / relative_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, dest_path)
                print("✅ Model migration completed")
        except Exception as e:
            print(f"⚠️  Model migration failed: {e}")

def verify_cache_setup():
    """Verify that cache directories are accessible and writable."""
    test_dirs = [
        os.environ.get("HF_HOME", "/runpod-volume/models"),
        os.environ.get("TRANSFORMERS_CACHE", "/runpod-volume/models"),
        os.environ.get("HF_HUB_CACHE", "/runpod-volume/models/hub"),
        os.environ.get("TORCH_HOME", "/runpod-volume/models/torch")
    ]
    
    for test_dir in test_dirs:
        try:
            # Test write permissions
            test_file = os.path.join(test_dir, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print(f"✅ Cache directory writable: {test_dir}")
        except Exception as e:
            print(f"❌ Cache directory not writable: {test_dir} - {e}")
            return False
    
    return True

def install_flash_attn():
    """Install CUDA-compatible flash_attn during startup - MUST happen before model loading."""
    print("🔍 Installing flash_attn before model downloads to prevent disk space issues...")
    
    try:
        # Check if flash_attn is already installed and working
        import flash_attn
        print("✅ flash_attn already installed and available")
        return True
    except ImportError:
        print("📦 flash_attn not found, proceeding with installation...")
    
    try:
        # Use the specific wheel that works for Python 3.11 + CUDA 12.x (RunPod environment)
        wheel_url = "https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.2/flash_attn-2.8.2+cu12torch2.6cxx11abiFALSE-cp311-cp311-linux_x86_64.whl"
        
        print("⚡ Installing CUDA 12.x + Python 3.11 compatible flash_attn...")
        print(f"🔄 Installing wheel: {wheel_url}")
        
        # Install with force to prevent any conflicts
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "--no-cache-dir", 
            "--force-reinstall", 
            "--no-deps",  # Skip dependencies to avoid conflicts
            wheel_url
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ flash_attn installation completed successfully")
            # Verify the installation works
            try:
                import flash_attn
                print("✅ flash_attn import verification successful")
                return True
            except ImportError as e:
                print(f"❌ flash_attn installed but import failed: {e}")
                return False
        else:
            print(f"❌ flash_attn wheel installation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error during flash_attn installation: {e}")
        return False

def sync_models_from_s3_cache():
    """
    Sync F5-TTS models from S3 to local cache for faster cold starts.
    This dramatically reduces cold start time by avoiding HuggingFace downloads.
    """
    try:
        # Import S3 sync function
        from s3_utils import sync_models_from_s3
        
        # Determine local cache directory (prefer persistent volume)
        local_cache_dirs = [
            "/runpod-volume/models",  # RunPod persistent volume (preferred)
            "/tmp/models",            # Temporary fallback
            "/app/models"             # Container fallback
        ]
        
        local_models_dir = None
        for cache_dir in local_cache_dirs:
            try:
                os.makedirs(cache_dir, exist_ok=True)
                # Test write access
                test_file = os.path.join(cache_dir, ".write_test")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                local_models_dir = cache_dir
                print(f"📁 Using local cache directory: {local_models_dir}")
                break
            except (OSError, PermissionError):
                print(f"⚠️ Cannot write to {cache_dir}, trying next option")
                continue
        
        if not local_models_dir:
            print("❌ No writable cache directory found")
            return False
        
        # Sync models from S3
        print("🔄 Starting S3 model sync for faster cold starts...")
        sync_success = sync_models_from_s3(
            local_models_dir=local_models_dir, 
            s3_models_prefix="models/"
        )
        
        if sync_success:
            # Update environment variables to point to synced models
            os.environ["HF_HOME"] = local_models_dir
            os.environ["TRANSFORMERS_CACHE"] = local_models_dir
            os.environ["HF_HUB_CACHE"] = os.path.join(local_models_dir, "hub")
            os.environ["TORCH_HOME"] = os.path.join(local_models_dir, "torch")
            
            print(f"✅ S3 model sync completed - models cached in {local_models_dir}")
            print(f"⚡ Cold start optimization: Models will load from local cache")
            return True
        else:
            print("⚠️ S3 model sync failed - will download from HuggingFace on first use")
            return False
            
    except ImportError:
        print("❌ S3 utils not available - skipping S3 model sync")
        return False
    except Exception as e:
        print(f"❌ S3 model sync error: {e}")
        return False


def upload_models_to_s3_cache():
    """
    Upload locally cached models to S3 for future cold start optimization.
    This should be called after models are downloaded/cached locally.
    """
    try:
        # Import S3 upload function
        from s3_utils import upload_models_to_s3
        
        # Find local model directories with content
        local_cache_dirs = [
            os.environ.get("HF_HOME", "/runpod-volume/models"),
            os.environ.get("TRANSFORMERS_CACHE", "/runpod-volume/models"),
            "/app/models",
            "/tmp/models"
        ]
        
        for local_models_dir in local_cache_dirs:
            if os.path.exists(local_models_dir) and os.listdir(local_models_dir):
                print(f"📤 Uploading models from {local_models_dir} to S3...")
                upload_success = upload_models_to_s3(
                    local_models_dir=local_models_dir,
                    s3_models_prefix="models/"
                )
                
                if upload_success:
                    print(f"✅ Models uploaded to S3 - future cold starts will be faster")
                    return True
                else:
                    print(f"⚠️ Model upload failed from {local_models_dir}")
        
        print("⚠️ No models found to upload to S3")
        return False
        
    except ImportError:
        print("❌ S3 utils not available - skipping S3 model upload")
        return False
    except Exception as e:
        print(f"❌ S3 model upload error: {e}")
        return False

def main():
    """Initialize model cache setup with S3 sync for faster cold starts."""
    print("🚀 Initializing F5-TTS model cache...")
    
    # CRITICAL: Install flash_attn FIRST before any model downloads/caching
    # This prevents disk space issues when models consume space before flash_attn installs
    print("🔥 Step 1: Installing flash_attn before model operations...")
    flash_attn_success = install_flash_attn()
    
    if not flash_attn_success:
        print("⚠️ flash_attn installation failed - continuing but performance may be degraded")
    
    # Step 2: Ensure directories exist
    print("📁 Step 2: Setting up cache directories...")
    ensure_cache_directories()
    
    # Step 3: Sync models from S3 for faster cold starts (after flash_attn is ready)
    print("☁️ Step 3: Syncing models from S3...")
    s3_sync_success = sync_models_from_s3_cache()
    
    # Step 4: Migrate existing models if any (fallback)
    print("🔄 Step 4: Migrating existing models...")
    migrate_existing_models()
    
    # Step 5: Verify cache setup
    print("✅ Step 5: Verifying cache setup...")
    cache_success = verify_cache_setup()
    
    if cache_success:
        if flash_attn_success:
            print("✅ Model cache and flash_attn initialization completed successfully")
            if s3_sync_success:
                print("⚡ S3 model cache ready - cold starts will be fast")
            else:
                print("📦 Models will be cached to S3 after first download")
        else:
            print("⚠️  Model cache ready, but flash_attn installation had issues")
        return 0
    else:
        print("❌ Model cache initialization failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())