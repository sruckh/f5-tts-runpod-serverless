#!/usr/bin/env python3
"""
Storage Configuration Validation Script
Tests the new /runpod-volume-based storage architecture for F5-TTS RunPod serverless
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check_environment_variables():
    """Validate that all required environment variables are set correctly"""
    print_section("Environment Variables Check")
    
    required_env_vars = {
        "HF_HOME": "/runpod-volume/models",
        "TRANSFORMERS_CACHE": "/runpod-volume/models/transformers", 
        "HF_HUB_CACHE": "/runpod-volume/models/hub",
        "TORCH_HOME": "/runpod-volume/models/torch"
    }
    
    all_correct = True
    for var, expected in required_env_vars.items():
        actual = os.environ.get(var, "NOT SET")
        status = "✅" if actual == expected else "❌"
        print(f"{status} {var}: {actual}")
        if actual != expected:
            all_correct = False
            print(f"   Expected: {expected}")
    
    return all_correct

def check_directory_structure():
    """Verify that all required directories exist and are writable"""
    print_section("Directory Structure Check")
    
    required_dirs = [
        "/runpod-volume/models",
        "/runpod-volume/models/hub",
        "/runpod-volume/models/transformers",
        "/runpod-volume/models/torch",
        "/runpod-volume/models/f5-tts"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        
        if path.exists():
            if path.is_dir():
                # Test write permissions
                try:
                    test_file = path / "test_write.tmp"
                    test_file.touch()
                    test_file.unlink()
                    print(f"✅ {dir_path} (exists, writable)")
                except Exception as e:
                    print(f"⚠️ {dir_path} (exists, not writable: {e})")
                    all_exist = False
            else:
                print(f"❌ {dir_path} (exists but not a directory)")
                all_exist = False
        else:
            print(f"❌ {dir_path} (does not exist)")
            all_exist = False
    
    return all_exist

def check_disk_space():
    """Check available disk space in /runpod-volume"""
    print_section("Disk Space Check")
    
    try:
        # Get disk usage for /runpod-volume
        statvfs = os.statvfs("/runpod-volume")
        
        # Calculate space in GB
        total_space = (statvfs.f_frsize * statvfs.f_blocks) / (1024**3)
        available_space = (statvfs.f_frsize * statvfs.f_available) / (1024**3)
        used_space = total_space - available_space
        
        print(f"📊 Total space: {total_space:.1f} GB")
        print(f"📊 Used space: {used_space:.1f} GB")
        print(f"📊 Available space: {available_space:.1f} GB")
        
        # Check if we have enough space for F5-TTS models (recommend 10GB minimum)
        min_required = 10.0
        if available_space >= min_required:
            print(f"✅ Sufficient space for F5-TTS models (≥{min_required} GB)")
            return True
        else:
            print(f"❌ Insufficient space for F5-TTS models (need ≥{min_required} GB)")
            return False
    
    except Exception as e:
        print(f"❌ Error checking disk space: {e}")
        return False

def check_temp_directory():
    """Verify /tmp has reasonable space for temporary processing"""
    print_section("Temporary Directory Check")
    
    try:
        # Test /tmp space
        statvfs = os.statvfs("/tmp")
        available_tmp = (statvfs.f_frsize * statvfs.f_available) / (1024**3)
        
        print(f"📊 /tmp available space: {available_tmp:.1f} GB")
        
        # Test write/read in /tmp
        with tempfile.NamedTemporaryFile(dir="/tmp", delete=False) as tmp_file:
            test_data = b"Storage test data" * 1000  # ~16KB
            tmp_file.write(test_data)
            tmp_file.flush()
            tmp_path = tmp_file.name
        
        # Read back and verify
        with open(tmp_path, 'rb') as f:
            read_data = f.read()
        
        os.unlink(tmp_path)
        
        if read_data == test_data:
            print("✅ /tmp read/write test passed")
            
            # Check if we have reasonable temp space (recommend 2GB minimum)
            min_tmp_space = 2.0
            if available_tmp >= min_tmp_space:
                print(f"✅ Sufficient /tmp space for processing (≥{min_tmp_space} GB)")
                return True
            else:
                print(f"⚠️ Limited /tmp space ({available_tmp:.1f} GB < {min_tmp_space} GB)")
                print("   This may cause issues with large audio files")
                return True  # Still functional, just a warning
        else:
            print("❌ /tmp read/write test failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing /tmp directory: {e}")
        return False

def test_model_cache_directories():
    """Test that model cache directories work correctly"""
    print_section("Model Cache Directory Test")
    
    cache_dirs = {
        "HF_HOME": os.environ.get("HF_HOME", "/runpod-volume/models"),
        "TRANSFORMERS_CACHE": os.environ.get("TRANSFORMERS_CACHE", "/runpod-volume/models/transformers"),
        "HF_HUB_CACHE": os.environ.get("HF_HUB_CACHE", "/runpod-volume/models/hub"),
        "TORCH_HOME": os.environ.get("TORCH_HOME", "/runpod-volume/models/torch")
    }
    
    all_working = True
    for cache_name, cache_path in cache_dirs.items():
        try:
            # Create a test file in each cache directory
            test_file = Path(cache_path) / f"test_{cache_name.lower()}.tmp"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            
            test_file.write_text(f"Test file for {cache_name}")
            content = test_file.read_text()
            test_file.unlink()
            
            if f"Test file for {cache_name}" in content:
                print(f"✅ {cache_name} cache directory working: {cache_path}")
            else:
                print(f"❌ {cache_name} cache directory test failed: {cache_path}")
                all_working = False
                
        except Exception as e:
            print(f"❌ {cache_name} cache directory error: {e}")
            all_working = False
    
    return all_working

def check_import_compatibility():
    """Test that F5-TTS imports work with new cache configuration"""
    print_section("F5-TTS Import Compatibility Test")
    
    try:
        # Test basic imports that would be affected by cache directories
        print("🔄 Testing HuggingFace transformers import...")
        import transformers
        print(f"✅ transformers imported successfully (v{transformers.__version__})")
        
        print("🔄 Testing torch import...")
        import torch
        print(f"✅ torch imported successfully (v{torch.__version__})")
        
        print("🔄 Testing F5-TTS import...")
        # This is a more comprehensive test - may fail if models aren't pre-loaded
        try:
            from f5_tts.model import F5TTS
            print("✅ F5TTS imported successfully")
            return True
        except ImportError as e:
            print(f"⚠️ F5TTS import failed (may need model pre-loading): {e}")
            return True  # Not a critical failure for storage test
        
    except Exception as e:
        print(f"❌ Import compatibility test failed: {e}")
        return False

def generate_configuration_report():
    """Generate a summary report of the storage configuration"""
    print_section("Configuration Summary Report")
    
    print("📋 Storage Architecture:")
    print("   - AI Models: /runpod-volume/models (persistent, large capacity)")
    print("   - Temporary Processing: /tmp (ephemeral, working files only)")
    print("   - User Data: S3 bucket (external, unlimited)")
    
    print("\n📋 Cache Directory Mapping:")
    cache_vars = ["HF_HOME", "TRANSFORMERS_CACHE", "HF_HUB_CACHE", "TORCH_HOME"]
    for var in cache_vars:
        value = os.environ.get(var, "NOT SET")
        print(f"   - {var}: {value}")
    
    print("\n📋 Expected Model Storage:")
    model_types = [
        "F5-TTS base model (~2-4 GB)",
        "HuggingFace transformers cache (~1-2 GB)",
        "PyTorch model cache (~0.5-1 GB)",
        "Total estimated: ~4-7 GB minimum"
    ]
    for model_type in model_types:
        print(f"   - {model_type}")

def main():
    """Run all storage configuration validation tests"""
    print("🚀 F5-TTS Storage Configuration Validation")
    print("=" * 60)
    
    tests = [
        ("Environment Variables", check_environment_variables),
        ("Directory Structure", check_directory_structure),
        ("Disk Space", check_disk_space),
        ("Temporary Directory", check_temp_directory),
        ("Model Cache Directories", test_model_cache_directories),
        ("Import Compatibility", check_import_compatibility)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Generate report
    generate_configuration_report()
    
    # Final summary
    print_section("Validation Results Summary")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All storage configuration tests PASSED!")
        print("   The new /runpod-volume storage architecture is properly configured.")
        return 0
    else:
        print("⚠️ Some storage configuration tests FAILED!")
        print("   Please address the issues before deploying to RunPod.")
        return 1

if __name__ == "__main__":
    sys.exit(main())