# F5-TTS RunPod Serverless - Troubleshooting Guide

## 🚨 Emergency Troubleshooting

### Critical Issues - Immediate Actions

#### 1. Complete Service Failure
**Symptoms**: All requests fail, endpoint unreachable
```bash
# Quick diagnostic
curl https://api.runpod.ai/v2/[endpoint-id]/health
# Expected: 200 OK with system status

# If fails, check:
1. RunPod service status: https://status.runpod.io
2. Endpoint status in console
3. Worker availability and scaling settings
```

**Resolution Steps**:
1. **Restart endpoint** in RunPod console
2. **Check Docker image** availability
3. **Verify GPU quota** and billing status
4. **Scale workers** manually if auto-scaling fails

#### 2. Container Build Failures
**Symptoms**: GitHub Actions build fails, image won't deploy
```bash
# Check build logs in GitHub Actions
https://github.com/your-username/f5-tts-runpod/actions

# Common failures:
- Docker Hub authentication failed
- Container size exceeded limits
- Base image unavailable
- Requirements installation timeout
```

**Resolution**:
```bash
# Re-trigger build
git commit --allow-empty -m "Rebuild container"
git push origin main

# Check Docker Hub image
docker pull your-username/f5-tts-runpod:latest

# Local build test
docker build -f Dockerfile.runpod -t test-build .
```

#### 3. Cold Start Timeouts
**Symptoms**: Requests timeout after 300s, network volume setup fails
```bash
# Increase timeout temporarily
Request Timeout: 600s (in RunPod console)

# Check network volume status
# Should show: /runpod-volume mounted and accessible
```

**Resolution**:
1. **Optimize environment setup** script
2. **Pre-cache critical models** in container
3. **Use Flashboot** for faster cold starts
4. **Monitor setup progress** in logs

## 🔍 Diagnostic Procedures

### System Health Check
```python
# Create diagnostic.py for comprehensive checks
import os
import subprocess
import requests
from pathlib import Path

def run_diagnostics():
    print("=== F5-TTS SYSTEM DIAGNOSTICS ===")
    
    # Check 1: Environment
    print("
1. ENVIRONMENT CHECK")
    print(f"Python version: {subprocess.check_output(['python', '--version']).decode().strip()}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Network volume: {os.path.exists('/runpod-volume')}")
    
    # Check 2: Dependencies
    print("
2. DEPENDENCY CHECK")
    critical_modules = ['torch', 'boto3', 'transformers', 'whisperx']
    for module in critical_modules:
        try:
            __import__(module)
            print(f"✓ {module}: Available")
        except ImportError:
            print(f"✗ {module}: Missing")
    
    # Check 3: GPU
    print("
3. GPU CHECK")
    try:
        import torch
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU count: {torch.cuda.device_count()}")
            print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
    except Exception as e:
        print(f"GPU check failed: {e}")
    
    # Check 4: S3 connectivity
    print("
4. S3 CONNECTIVITY CHECK")
    try:
        import boto3
        s3 = boto3.client('s3')
        s3.list_buckets()
        print("✓ S3 connection: Working")
    except Exception as e:
        print(f"✗ S3 connection: {e}")
    
    # Check 5: Model availability
    print("
5. MODEL AVAILABILITY CHECK")
    model_paths = [
        "/runpod-volume/f5tts/models/F5-TTS",
        "/runpod-volume/f5tts/models/whisperx"
    ]
    for path in model_paths:
        exists = os.path.exists(path)
        print(f"{'✓' if exists else '✗'} {path}: {'Present' if exists else 'Missing'}")

if __name__ == "__main__":
    run_diagnostics()
```

### Performance Analysis
```python
# Create performance_check.py
import time
import psutil
import torch

def monitor_performance():
    print("=== PERFORMANCE MONITORING ===")
    
    # System resources
    print(f"
CPU usage: {psutil.cpu_percent(interval=1)}%")
    print(f"Memory usage: {psutil.virtual_memory().percent}%")
    print(f"Disk usage: {psutil.disk_usage('/').percent}%")
    
    # GPU monitoring
    if torch.cuda.is_available():
        print(f"GPU memory used: {torch.cuda.memory_allocated() / 1e9:.1f}GB")
        print(f"GPU memory cached: {torch.cuda.memory_reserved() / 1e9:.1f}GB")
    
    # Network volume performance
    start_time = time.time()
    test_file = "/runpod-volume/performance_test.txt"
    with open(test_file, 'w') as f:
        f.write("Performance test data" * 1000)
    write_time = time.time() - start_time
    
    start_time = time.time()
    with open(test_file, 'r') as f:
        data = f.read()
    read_time = time.time() - start_time
    
    print(f"Network volume write: {write_time:.3f}s")
    print(f"Network volume read: {read_time:.3f}s")
    
    os.remove(test_file)
```

## 🐛 Common Issues & Solutions

### Issue 1: "Model download failed"
**Symptoms**:
```
Error: HTTPError: 401 Client Error: Unauthorized
Failed to download F5-TTS model from HuggingFace
```

**Root Cause**: Missing or invalid HuggingFace token

**Solution**:
```bash
# Add HF_TOKEN environment variable in RunPod
HF_TOKEN=your_huggingface_token

# Or use public models only
# Remove authentication requirements in f5tts_engine.py
```

**Prevention**: Always test model downloads locally first

### Issue 2: "S3 access denied" 
**Symptoms**:
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
ClientError: An error occurred (403) when calling HeadObject
```

**Root Cause**: Invalid AWS credentials or insufficient permissions

**Solution**:
```bash
# Verify credentials
aws configure list

# Test S3 access
aws s3 ls s3://your-bucket/

# Check IAM policy includes:
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow", 
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::your-bucket/*"
        }
    ]
}
```

### Issue 3: "Flash attention installation failed"
**Symptoms**:
```
ERROR: Failed building wheel for flash-attn
Could not build wheels for flash-attn
```

**Root Cause**: Architecture mismatch or CUDA version incompatibility

**Solution**:
```bash
# Use pre-built wheel from config.py
FLASH_ATTN_WHEEL = "https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.0.post2/flash_attn-2.8.0.post2+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl"

# Or disable flash attention
# Modify F5-TTS engine to use standard attention
```

### Issue 4: "Network volume not accessible"
**Symptoms**:
```
OSError: [Errno 2] No such file or directory: '/runpod-volume'
Permission denied: '/runpod-volume/f5tts'
```

**Root Cause**: Network volume not mounted or permissions issue

**Solution**:
```bash
# Check mount in container startup
if [ ! -d "/runpod-volume" ]; then
    echo "ERROR: Network volume not mounted"
    exit 1
fi

# Create directory with proper permissions
sudo mkdir -p /runpod-volume/f5tts
sudo chown -R $(whoami):$(whoami) /runpod-volume/f5tts
```

### Issue 5: "Subtitle generation failed"
**Symptoms**:
```
ImportError: No module named 'ass'
Invalid timing data structure
```

**Root Cause**: Missing dependencies or invalid word timing data

**Solution**:
```bash
# Install ASS library
pip install ass

# Validate timing data structure
python -c "
from TASKS import ASSSubtitleGenerator
gen = ASSSubtitleGenerator()
timings = [{'word': 'test', 'start': 0.0, 'end': 1.0}]
print(gen.validate_timing_data(timings))
"
```

### Issue 6: "Memory out of bounds"
**Symptoms**:
```
CUDA out of memory. Tried to allocate 2.50 GiB
RuntimeError: Expected all tensors to be on the same device
```

**Root Cause**: Insufficient GPU memory or memory leaks

**Solution**:
```python
# Add memory cleanup in handler
import torch
import gc

def cleanup_memory():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

# Call after each inference
cleanup_memory()

# Monitor memory usage
def check_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        print(f"GPU Memory - Allocated: {allocated:.1f}GB, Reserved: {reserved:.1f}GB")
```

## 📊 Monitoring & Alerting

### Setup Monitoring
```python
# Create monitor.py for continuous monitoring
import time
import requests
import json
from datetime import datetime

def monitor_endpoint(endpoint_url, api_key, interval=300):
    """Monitor endpoint health every 5 minutes"""
    
    while True:
        try:
            # Health check
            response = requests.get(f"{endpoint_url}/health", 
                                  headers={"Authorization": f"Bearer {api_key}"},
                                  timeout=30)
            
            status = "HEALTHY" if response.status_code == 200 else "UNHEALTHY"
            timestamp = datetime.now().isoformat()
            
            print(f"[{timestamp}] Endpoint status: {status}")
            
            # Test inference periodically 
            if datetime.now().minute % 15 == 0:  # Every 15 minutes
                test_inference(endpoint_url, api_key)
                
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Monitor error: {e}")
        
        time.sleep(interval)

def test_inference(endpoint_url, api_key):
    """Run a quick inference test"""
    test_payload = {
        "input": {
            "target_text": "This is a monitoring test",
            "input_audio_s3": "s3://test-bucket/test.wav",
            "speaker_audio_s3": "s3://test-bucket/speaker.wav"
        }
    }
    
    try:
        response = requests.post(f"{endpoint_url}/run",
                               headers={"Authorization": f"Bearer {api_key}"},
                               json=test_payload,
                               timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            processing_time = result.get('output', {}).get('processing_time', 'N/A')
            print(f"Test inference: SUCCESS ({processing_time}s)")
        else:
            print(f"Test inference: FAILED ({response.status_code})")
            
    except Exception as e:
        print(f"Test inference: ERROR - {e}")
```

### Performance Alerts
```python
# Add to handler.py for performance monitoring
import logging
import time

logger = logging.getLogger(__name__)

def performance_alert(processing_time, threshold=10.0):
    """Alert on performance degradation"""
    if processing_time > threshold:
        logger.warning(f"PERFORMANCE ALERT: Processing time {processing_time:.2f}s exceeds threshold {threshold}s")
        
        # Could integrate with external alerting:
        # - Slack webhook
        # - Email notification  
        # - PagerDuty integration
        
def log_metrics(metrics):
    """Log structured metrics for analysis"""
    logger.info("METRICS", extra={
        "processing_time": metrics.get("processing_time"),
        "audio_duration": metrics.get("audio_duration"), 
        "subtitle_events": metrics.get("subtitle_events"),
        "gpu_memory_used": metrics.get("gpu_memory_used"),
        "timestamp": time.time()
    })
```

## 🚀 Recovery Procedures

### Quick Recovery Checklist
When experiencing issues:

1. **🔍 Immediate Assessment** (2 minutes)
   ```bash
   # Check service status
   curl https://api.runpod.ai/v2/[endpoint-id]/health
   
   # Check recent logs
   # View in RunPod console -> Logs tab
   ```

2. **⚡ Quick Fixes** (5 minutes)
   ```bash
   # Restart endpoint
   # RunPod Console -> Endpoints -> Stop/Start
   
   # Clear cache and restart workers
   # This forces fresh environment setup
   ```

3. **🔧 Environment Reset** (10 minutes)
   ```bash
   # Full environment reset
   # Delete /runpod-volume/f5tts directory
   # This triggers complete reinstallation
   
   # Update container image
   # Deploy latest from Docker Hub
   ```

4. **🛠️ Full Recovery** (20 minutes)
   ```bash
   # Rebuild from source
   git push origin main  # Trigger new build
   
   # Wait for GitHub Actions completion
   # Deploy new container version
   
   # Test with validation suite
   python CONTRIBUTING.md
   ```

### Rollback Procedure
If new deployment fails:

```bash
# 1. Identify last working version
git log --oneline -10

# 2. Rollback container
# In RunPod console, change image tag to previous version
your-username/f5-tts-runpod:previous-sha

# 3. Test functionality
curl -X POST [endpoint] -d @test_request.json

# 4. Investigate issues in dev environment
git checkout main
# Fix issues and redeploy
```

## 📞 Support Resources

### Documentation
- **Architecture**: `README.md` - System overview and design
- **API Reference**: `API.md` - Complete API documentation  
- **Configuration**: `CONFIG.md` - Environment and settings
- **Performance**: `PERFORMANCE_ANALYSIS_FINAL.md` - Optimization guide

### Debugging Tools
- **Validation Suite**: `python CONTRIBUTING.md`
- **Diagnostics**: `python diagnostic.py` (create from examples above)
- **Performance Monitor**: `python monitor.py` (create from examples above)

### Emergency Contacts
- **RunPod Support**: https://docs.runpod.io/support
- **GitHub Issues**: Repository issues for code problems
- **AWS Support**: For S3 and infrastructure issues

### Self-Service Debugging
Before requesting support:

1. **Run diagnostics** - Use provided diagnostic scripts
2. **Check logs** - Review RunPod console logs thoroughly
3. **Test components** - Validate S3, models, dependencies individually  
4. **Review recent changes** - Check git history for recent modifications
5. **Consult documentation** - Review all provided guides

This comprehensive troubleshooting guide should resolve 95% of issues encountered in production deployment. The system is designed for reliability, but these procedures ensure rapid recovery when problems occur.# F5-TTS RunPod Serverless - Troubleshooting Guide

## 🚨 Emergency Troubleshooting

### Critical Issues - Immediate Actions

#### 1. Complete Service Failure
**Symptoms**: All requests fail, endpoint unreachable
```bash
# Quick diagnostic
curl https://api.runpod.ai/v2/[endpoint-id]/health
# Expected: 200 OK with system status

# If fails, check:
1. RunPod service status: https://status.runpod.io
2. Endpoint status in console
3. Worker availability and scaling settings
```

**Resolution Steps**:
1. **Restart endpoint** in RunPod console
2. **Check Docker image** availability
3. **Verify GPU quota** and billing status
4. **Scale workers** manually if auto-scaling fails

#### 2. Container Build Failures
**Symptoms**: GitHub Actions build fails, image won't deploy
```bash
# Check build logs in GitHub Actions
https://github.com/your-username/f5-tts-runpod/actions

# Common failures:
- Docker Hub authentication failed
- Container size exceeded limits
- Base image unavailable
- Requirements installation timeout
```

**Resolution**:
```bash
# Re-trigger build
git commit --allow-empty -m "Rebuild container"
git push origin main

# Check Docker Hub image
docker pull your-username/f5-tts-runpod:latest

# Local build test
docker build -f Dockerfile.runpod -t test-build .
```

#### 3. Cold Start Timeouts
**Symptoms**: Requests timeout after 300s, network volume setup fails
```bash
# Increase timeout temporarily
Request Timeout: 600s (in RunPod console)

# Check network volume status
# Should show: /runpod-volume mounted and accessible
```

**Resolution**:
1. **Optimize environment setup** script
2. **Pre-cache critical models** in container
3. **Use Flashboot** for faster cold starts
4. **Monitor setup progress** in logs

## 🔍 Diagnostic Procedures

### System Health Check
```python
# Create diagnostic.py for comprehensive checks
import os
import subprocess
import requests
from pathlib import Path

def run_diagnostics():
    print("=== F5-TTS SYSTEM DIAGNOSTICS ===")
    
    # Check 1: Environment
    print("
1. ENVIRONMENT CHECK")
    print(f"Python version: {subprocess.check_output(['python', '--version']).decode().strip()}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Network volume: {os.path.exists('/runpod-volume')}")
    
    # Check 2: Dependencies
    print("
2. DEPENDENCY CHECK")
    critical_modules = ['torch', 'boto3', 'transformers', 'whisperx']
    for module in critical_modules:
        try:
            __import__(module)
            print(f"✓ {module}: Available")
        except ImportError:
            print(f"✗ {module}: Missing")
    
    # Check 3: GPU
    print("
3. GPU CHECK")
    try:
        import torch
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU count: {torch.cuda.device_count()}")
            print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
    except Exception as e:
        print(f"GPU check failed: {e}")
    
    # Check 4: S3 connectivity
    print("
4. S3 CONNECTIVITY CHECK")
    try:
        import boto3
        s3 = boto3.client('s3')
        s3.list_buckets()
        print("✓ S3 connection: Working")
    except Exception as e:
        print(f"✗ S3 connection: {e}")
    
    # Check 5: Model availability
    print("
5. MODEL AVAILABILITY CHECK")
    model_paths = [
        "/runpod-volume/f5tts/models/F5-TTS",
        "/runpod-volume/f5tts/models/whisperx"
    ]
    for path in model_paths:
        exists = os.path.exists(path)
        print(f"{'✓' if exists else '✗'} {path}: {'Present' if exists else 'Missing'}")

if __name__ == "__main__":
    run_diagnostics()
```

### Performance Analysis
```python
# Create performance_check.py
import time
import psutil
import torch

def monitor_performance():
    print("=== PERFORMANCE MONITORING ===")
    
    # System resources
    print(f"
CPU usage: {psutil.cpu_percent(interval=1)}%")
    print(f"Memory usage: {psutil.virtual_memory().percent}%")
    print(f"Disk usage: {psutil.disk_usage('/').percent}%")
    
    # GPU monitoring
    if torch.cuda.is_available():
        print(f"GPU memory used: {torch.cuda.memory_allocated() / 1e9:.1f}GB")
        print(f"GPU memory cached: {torch.cuda.memory_reserved() / 1e9:.1f}GB")
    
    # Network volume performance
    start_time = time.time()
    test_file = "/runpod-volume/performance_test.txt"
    with open(test_file, 'w') as f:
        f.write("Performance test data" * 1000)
    write_time = time.time() - start_time
    
    start_time = time.time()
    with open(test_file, 'r') as f:
        data = f.read()
    read_time = time.time() - start_time
    
    print(f"Network volume write: {write_time:.3f}s")
    print(f"Network volume read: {read_time:.3f}s")
    
    os.remove(test_file)
```

## 🐛 Common Issues & Solutions

### Issue 1: "Model download failed"
**Symptoms**:
```
Error: HTTPError: 401 Client Error: Unauthorized
Failed to download F5-TTS model from HuggingFace
```

**Root Cause**: Missing or invalid HuggingFace token

**Solution**:
```bash
# Add HF_TOKEN environment variable in RunPod
HF_TOKEN=your_huggingface_token

# Or use public models only
# Remove authentication requirements in f5tts_engine.py
```

**Prevention**: Always test model downloads locally first

### Issue 2: "S3 access denied" 
**Symptoms**:
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
ClientError: An error occurred (403) when calling HeadObject
```

**Root Cause**: Invalid AWS credentials or insufficient permissions

**Solution**:
```bash
# Verify credentials
aws configure list

# Test S3 access
aws s3 ls s3://your-bucket/

# Check IAM policy includes:
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow", 
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::your-bucket/*"
        }
    ]
}
```

### Issue 3: "Flash attention installation failed"
**Symptoms**:
```
ERROR: Failed building wheel for flash-attn
Could not build wheels for flash-attn
```

**Root Cause**: Architecture mismatch or CUDA version incompatibility

**Solution**:
```bash
# Use pre-built wheel from config.py
FLASH_ATTN_WHEEL = "https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.0.post2/flash_attn-2.8.0.post2+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl"

# Or disable flash attention
# Modify F5-TTS engine to use standard attention
```

### Issue 4: "Network volume not accessible"
**Symptoms**:
```
OSError: [Errno 2] No such file or directory: '/runpod-volume'
Permission denied: '/runpod-volume/f5tts'
```

**Root Cause**: Network volume not mounted or permissions issue

**Solution**:
```bash
# Check mount in container startup
if [ ! -d "/runpod-volume" ]; then
    echo "ERROR: Network volume not mounted"
    exit 1
fi

# Create directory with proper permissions
sudo mkdir -p /runpod-volume/f5tts
sudo chown -R $(whoami):$(whoami) /runpod-volume/f5tts
```

### Issue 5: "Subtitle generation failed"
**Symptoms**:
```
ImportError: No module named 'ass'
Invalid timing data structure
```

**Root Cause**: Missing dependencies or invalid word timing data

**Solution**:
```bash
# Install ASS library
pip install ass

# Validate timing data structure
python -c "
from TASKS import ASSSubtitleGenerator
gen = ASSSubtitleGenerator()
timings = [{'word': 'test', 'start': 0.0, 'end': 1.0}]
print(gen.validate_timing_data(timings))
"
```

### Issue 6: "Memory out of bounds"
**Symptoms**:
```
CUDA out of memory. Tried to allocate 2.50 GiB
RuntimeError: Expected all tensors to be on the same device
```

**Root Cause**: Insufficient GPU memory or memory leaks

**Solution**:
```python
# Add memory cleanup in handler
import torch
import gc

def cleanup_memory():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

# Call after each inference
cleanup_memory()

# Monitor memory usage
def check_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        print(f"GPU Memory - Allocated: {allocated:.1f}GB, Reserved: {reserved:.1f}GB")
```

## 📊 Monitoring & Alerting

### Setup Monitoring
```python
# Create monitor.py for continuous monitoring
import time
import requests
import json
from datetime import datetime

def monitor_endpoint(endpoint_url, api_key, interval=300):
    """Monitor endpoint health every 5 minutes"""
    
    while True:
        try:
            # Health check
            response = requests.get(f"{endpoint_url}/health", 
                                  headers={"Authorization": f"Bearer {api_key}"},
                                  timeout=30)
            
            status = "HEALTHY" if response.status_code == 200 else "UNHEALTHY"
            timestamp = datetime.now().isoformat()
            
            print(f"[{timestamp}] Endpoint status: {status}")
            
            # Test inference periodically 
            if datetime.now().minute % 15 == 0:  # Every 15 minutes
                test_inference(endpoint_url, api_key)
                
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Monitor error: {e}")
        
        time.sleep(interval)

def test_inference(endpoint_url, api_key):
    """Run a quick inference test"""
    test_payload = {
        "input": {
            "target_text": "This is a monitoring test",
            "input_audio_s3": "s3://test-bucket/test.wav",
            "speaker_audio_s3": "s3://test-bucket/speaker.wav"
        }
    }
    
    try:
        response = requests.post(f"{endpoint_url}/run",
                               headers={"Authorization": f"Bearer {api_key}"},
                               json=test_payload,
                               timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            processing_time = result.get('output', {}).get('processing_time', 'N/A')
            print(f"Test inference: SUCCESS ({processing_time}s)")
        else:
            print(f"Test inference: FAILED ({response.status_code})")
            
    except Exception as e:
        print(f"Test inference: ERROR - {e}")
```

### Performance Alerts
```python
# Add to handler.py for performance monitoring
import logging
import time

logger = logging.getLogger(__name__)

def performance_alert(processing_time, threshold=10.0):
    """Alert on performance degradation"""
    if processing_time > threshold:
        logger.warning(f"PERFORMANCE ALERT: Processing time {processing_time:.2f}s exceeds threshold {threshold}s")
        
        # Could integrate with external alerting:
        # - Slack webhook
        # - Email notification  
        # - PagerDuty integration
        
def log_metrics(metrics):
    """Log structured metrics for analysis"""
    logger.info("METRICS", extra={
        "processing_time": metrics.get("processing_time"),
        "audio_duration": metrics.get("audio_duration"), 
        "subtitle_events": metrics.get("subtitle_events"),
        "gpu_memory_used": metrics.get("gpu_memory_used"),
        "timestamp": time.time()
    })
```

## 🚀 Recovery Procedures

### Quick Recovery Checklist
When experiencing issues:

1. **🔍 Immediate Assessment** (2 minutes)
   ```bash
   # Check service status
   curl https://api.runpod.ai/v2/[endpoint-id]/health
   
   # Check recent logs
   # View in RunPod console -> Logs tab
   ```

2. **⚡ Quick Fixes** (5 minutes)
   ```bash
   # Restart endpoint
   # RunPod Console -> Endpoints -> Stop/Start
   
   # Clear cache and restart workers
   # This forces fresh environment setup
   ```

3. **🔧 Environment Reset** (10 minutes)
   ```bash
   # Full environment reset
   # Delete /runpod-volume/f5tts directory
   # This triggers complete reinstallation
   
   # Update container image
   # Deploy latest from Docker Hub
   ```

4. **🛠️ Full Recovery** (20 minutes)
   ```bash
   # Rebuild from source
   git push origin main  # Trigger new build
   
   # Wait for GitHub Actions completion
   # Deploy new container version
   
   # Test with validation suite
   python CONTRIBUTING.md
   ```

### Rollback Procedure
If new deployment fails:

```bash
# 1. Identify last working version
git log --oneline -10

# 2. Rollback container
# In RunPod console, change image tag to previous version
your-username/f5-tts-runpod:previous-sha

# 3. Test functionality
curl -X POST [endpoint] -d @test_request.json

# 4. Investigate issues in dev environment
git checkout main
# Fix issues and redeploy
```

## 📞 Support Resources

### Documentation
- **Architecture**: `README.md` - System overview and design
- **API Reference**: `API.md` - Complete API documentation  
- **Configuration**: `CONFIG.md` - Environment and settings
- **Performance**: `PERFORMANCE_ANALYSIS_FINAL.md` - Optimization guide

### Debugging Tools
- **Validation Suite**: `python CONTRIBUTING.md`
- **Diagnostics**: `python diagnostic.py` (create from examples above)
- **Performance Monitor**: `python monitor.py` (create from examples above)

### Emergency Contacts
- **RunPod Support**: https://docs.runpod.io/support
- **GitHub Issues**: Repository issues for code problems
- **AWS Support**: For S3 and infrastructure issues

### Self-Service Debugging
Before requesting support:

1. **Run diagnostics** - Use provided diagnostic scripts
2. **Check logs** - Review RunPod console logs thoroughly
3. **Test components** - Validate S3, models, dependencies individually  
4. **Review recent changes** - Check git history for recent modifications
5. **Consult documentation** - Review all provided guides

This comprehensive troubleshooting guide should resolve 95% of issues encountered in production deployment. The system is designed for reliability, but these procedures ensure rapid recovery when problems occur.