#!/usr/bin/env python3
"""
Model cache initialization script for F5-TTS RunPod deployment.
Ensures models are properly cached in persistent storage.
"""

import os
import sys
import shutil
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

def main():
    """Initialize model cache setup."""
    print("🚀 Initializing F5-TTS model cache...")
    
    # Ensure directories exist
    ensure_cache_directories()
    
    # Migrate existing models if any
    migrate_existing_models()
    
    # Verify setup
    if verify_cache_setup():
        print("✅ Model cache initialization completed successfully")
        return 0
    else:
        print("❌ Model cache initialization failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())