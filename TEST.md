# TEST.md

## Testing Strategy

### Test Pyramid for F5-TTS Serverless
```
         /\
        /  \  End-to-End API Tests (20%)
       /----\
      /      \  Integration Tests (30%)
     /--------\
    /          \  Unit Tests (50%)
   /____________\
```

## Test Stack

### Testing Frameworks
- **Unit Tests**: Python unittest, pytest
- **Integration Tests**: Docker containers, S3 mocking
- **API Tests**: curl, RunPod API testing
- **Performance Tests**: Load testing with multiple requests
- **Model Tests**: F5-TTS inference validation

## Running Tests

### Local Testing Commands
```bash
# Test basic functionality
python -m unittest test_handler.py

# Test with Docker container
docker run --gpus all -p 8000:8000 f5-tts-serverless:test

# Test API endpoints
python test_api_endpoints.py

# Test S3 integration
python test_s3_integration.py

# Test voice model loading
python test_voice_models.py

# Performance testing
python test_performance.py
```

### Container Testing
```bash
# Build test container
docker build -f Dockerfile.runpod -t f5-tts-test:latest .

# Run container with test configuration
docker run --gpus all -p 8000:8000 \
  -e S3_BUCKET=test-bucket \
  -e AWS_ACCESS_KEY_ID=test-key \
  -e AWS_SECRET_ACCESS_KEY=test-secret \
  f5-tts-test:latest
```

### RunPod API Testing
```bash
# Test endpoint deployment
curl -X POST "https://api.runpod.ai/v2/{endpoint-id}/runsync" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input": {"text": "Test message"}}'
```

## Test Structure

### Unit Test Example
```python
# test_handler.py
import unittest
from unittest.mock import patch, MagicMock
from runpod_handler import handler

class TestRunPodHandler(unittest.TestCase):
    
    def test_basic_tts_generation(self):
        """Test basic TTS generation functionality"""
        event = {
            "input": {
                "text": "Hello world test"
            }
        }
        
        with patch('runpod_handler.F5TTS') as mock_f5tts:
            mock_f5tts.return_value.generate.return_value = ("test_audio.wav", 2.5)
            
            result = handler(event)
            
            self.assertIn("audio_url", result)
            self.assertEqual(result["duration"], 2.5)
    
    def test_voice_upload_validation(self):
        """Test voice upload input validation"""
        event = {
            "input": {
                "endpoint": "upload",
                "voice_name": "test.wav"
                # Missing required fields
            }
        }
        
        result = handler(event)
        self.assertIn("error", result)
        self.assertIn("voice_file_url", result["error"])
```

### Integration Test Example
```python
# test_s3_integration.py
import unittest
import boto3
from moto import mock_s3
from s3_utils import upload_file, download_file

class TestS3Integration(unittest.TestCase):
    
    @mock_s3
    def setUp(self):
        """Set up mock S3 environment"""
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.bucket_name = 'test-bucket'
        self.s3_client.create_bucket(Bucket=self.bucket_name)
    
    @mock_s3
    def test_voice_file_upload(self):
        """Test voice file upload to S3"""
        test_file_path = "/tmp/test_voice.wav"
        s3_key = "voices/test_voice.wav"
        
        # Create test file
        with open(test_file_path, 'wb') as f:
            f.write(b"fake audio data")
        
        # Upload to S3
        result = upload_file(test_file_path, s3_key)
        self.assertTrue(result)
        
        # Verify file exists in S3
        objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        self.assertEqual(len(objects['Contents']), 1)
        self.assertEqual(objects['Contents'][0]['Key'], s3_key)
```

### API Test Example
```python
# test_api_endpoints.py
import requests
import json
import time

class TestF5TTSAPI:
    
    def __init__(self, endpoint_url, api_key):
        self.endpoint_url = endpoint_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def test_tts_generation(self):
        """Test basic TTS generation endpoint"""
        payload = {
            "input": {
                "text": "This is a test of the F5-TTS API endpoint",
                "speed": 1.0
            }
        }
        
        response = requests.post(self.endpoint_url, 
                               headers=self.headers, 
                               json=payload)
        
        assert response.status_code == 200
        result = response.json()
        assert "audio_url" in result
        assert "duration" in result
        assert result["duration"] > 0
        
        print(f"✅ TTS Generation: {result['duration']}s audio generated")
    
    def test_voice_upload(self):
        """Test voice upload endpoint"""
        payload = {
            "input": {
                "endpoint": "upload",
                "voice_name": "test_voice.wav",
                "voice_file_url": "https://example.com/test_voice.wav",
                "text_file_url": "https://example.com/test_voice.txt"
            }
        }
        
        response = requests.post(self.endpoint_url,
                               headers=self.headers,
                               json=payload)
        
        assert response.status_code == 200
        result = response.json()
        assert "status" in result
        assert "uploaded successfully" in result["status"]
        
        print("✅ Voice Upload: Success")
    
    def test_list_voices(self):
        """Test list voices endpoint"""
        payload = {
            "input": {
                "endpoint": "list_voices"
            }
        }
        
        response = requests.post(self.endpoint_url,
                               headers=self.headers,
                               json=payload)
        
        assert response.status_code == 200
        result = response.json()
        assert "voices" in result
        assert isinstance(result["voices"], list)
        
        print(f"✅ List Voices: Found {len(result['voices'])} voices")

# Usage
if __name__ == "__main__":
    api_test = TestF5TTSAPI(
        endpoint_url="https://api.runpod.ai/v2/your-endpoint/runsync",
        api_key="your-api-key"
    )
    
    api_test.test_tts_generation()
    api_test.test_voice_upload()
    api_test.test_list_voices()
```

## Test Coverage Goals

### Coverage Targets for F5-TTS
```
Handler Functions: 90%
S3 Integration: 85%
Error Handling: 80%
API Endpoints: 95%
```

### Performance Benchmarks
```
Cold Start: < 5 seconds
TTS Generation: < 3 seconds per 10 words
Voice Upload: < 10 seconds per file
S3 Operations: < 2 seconds per file
```

## Common Test Scenarios

### TTS Generation Tests
- Basic text input validation
- Voice file parameter handling
- Speed parameter validation
- Output audio file validation
- Error handling for invalid input

### Voice Management Tests
- Voice file upload validation
- Text file upload validation
- Voice listing functionality
- Voice file deletion
- Invalid file format handling

### S3 Integration Tests
- File upload success/failure
- File download validation
- Bucket connectivity
- Permission handling
- Large file handling

### Model Loading Tests
- F5-TTS model initialization
- Flash attention compatibility
- CUDA memory allocation
- Model caching validation

## Performance Testing

### Load Testing
```python
# test_performance.py
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

async def stress_test_endpoint(endpoint_url, api_key, num_requests=50):
    """Stress test the TTS endpoint"""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "input": {
            "text": "Performance test message for load testing",
            "speed": 1.0
        }
    }
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        tasks = []
        for i in range(num_requests):
            task = session.post(endpoint_url, headers=headers, json=payload)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        success_count = sum(1 for r in responses if r.status == 200)
        
        print(f"Load Test Results:")
        print(f"Total Requests: {num_requests}")
        print(f"Successful: {success_count}")
        print(f"Failed: {num_requests - success_count}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Requests/sec: {num_requests/total_time:.2f}")
```

### Memory Testing
```python
# test_memory_usage.py
import psutil
import time
from runpod_handler import handler

def test_memory_usage():
    """Test memory usage during TTS generation"""
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Generate multiple TTS samples
    for i in range(10):
        event = {
            "input": {
                "text": f"Memory test message number {i+1}"
            }
        }
        
        result = handler(event)
        current_memory = process.memory_info().rss / 1024 / 1024
        
        print(f"Request {i+1}: {current_memory:.1f}MB (+{current_memory-initial_memory:.1f}MB)")
    
    final_memory = process.memory_info().rss / 1024 / 1024
    memory_increase = final_memory - initial_memory
    
    print(f"Final Memory Usage: {final_memory:.1f}MB")
    print(f"Memory Increase: {memory_increase:.1f}MB")
    
    # Check for memory leaks
    assert memory_increase < 500, f"Potential memory leak: {memory_increase}MB increase"
```

## Debugging Tests

### Debug Commands
```bash
# Run tests with verbose output
python -m pytest -v test_handler.py

# Run specific test with debugging
python -m pytest -v -s test_handler.py::TestRunPodHandler::test_basic_tts_generation

# Run with coverage report
python -m pytest --cov=runpod_handler test_handler.py

# Run performance tests
python test_performance.py
```

### Common Issues
1. **CUDA Memory Issues**: Monitor GPU memory usage during tests
2. **S3 Connection Failures**: Use mocked S3 for unit tests
3. **Model Loading Errors**: Verify F5-TTS installation
4. **Timeout Issues**: Increase test timeouts for model loading

## Keywords <!-- #keywords -->
testing, F5-TTS, RunPod, serverless, API testing, performance testing, unit tests, integration tests, S3 testing, model validation, load testing, memory testing