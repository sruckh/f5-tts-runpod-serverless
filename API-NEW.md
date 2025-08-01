# F5-TTS RunPod Serverless API Documentation

## 🎯 Overview

The F5-TTS RunPod Serverless API provides high-quality text-to-speech synthesis using the F5-TTS model. This implementation follows **proper serverless architecture** with synchronous processing and immediate results.

**🚀 Key Features:**
- **Synchronous API**: Get results immediately, no polling needed
- **Pre-loaded Models**: Sub-second cold starts with build-time optimization
- **Voice Cloning**: Upload custom voice files for personalized TTS
- **S3 Integration**: Automatic file storage and retrieval
- **High Performance**: Optimized for RunPod serverless infrastructure

## 📡 Base URL

```
https://api.runpod.ai/v2/{your-endpoint-id}/runsync
```

All requests are **POST** requests to the RunPod synchronous endpoint.

## 🎵 TTS Generation

Generate speech from text with optional voice cloning.

**Endpoint:** `POST /runsync`

### Request Format

```json
{
  "input": {
    "text": "Text to synthesize (required)",
    "local_voice": "voice-file.wav (optional)",
    "speed": 1.0
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | ✅ Yes | Text to convert to speech |
| `local_voice` | string | ❌ No | Voice file name (from S3) or URL |
| `speed` | float | ❌ No | Speech speed multiplier (default: 1.0) |

### Response Format

```json
{
  "audio_url": "https://s3.amazonaws.com/bucket/output/audio.wav",
  "duration": 3.25,
  "text": "Text to synthesize",
  "status": "completed"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `audio_url` | string | Public URL to generated audio file |
| `duration` | float | Audio duration in seconds |
| `text` | string | Original input text |
| `status` | string | Always "completed" for successful requests |

### Example Request

```bash
curl -X POST "https://api.runpod.ai/v2/{endpoint-id}/runsync" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {api-key}" \
  -d '{
    "input": {
      "text": "Welcome to F5-TTS serverless API! This is a demonstration of high-quality text-to-speech synthesis.",
      "local_voice": "sarah-voice.wav",
      "speed": 1.1
    }
  }'
```

### Example Response

```json
{
  "audio_url": "https://s3.amazonaws.com/my-bucket/output/f47ac10b-58cc-4372-a567-0e02b2c3d479.wav",
  "duration": 4.8,
  "text": "Welcome to F5-TTS serverless API! This is a demonstration of high-quality text-to-speech synthesis.",
  "status": "completed"
}
```

## 📤 Voice Upload

Upload custom voice files for voice cloning.

**Endpoint:** `POST /runsync`

### Request Format

```json
{
  "input": {
    "endpoint": "upload",
    "voice_file_url": "https://example.com/voice.wav",
    "voice_name": "my-custom-voice.wav"
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `endpoint` | string | ✅ Yes | Must be "upload" |
| `voice_file_url` | string | ✅ Yes | URL to voice file to download |
| `voice_name` | string | ✅ Yes | Name to save voice file as |

### Response Format

```json
{
  "status": "Voice 'my-custom-voice.wav' uploaded successfully",
  "message": "F5-TTS will automatically transcribe the reference audio"
}
```

### Voice File Requirements

- **Format**: WAV, MP3, or other common audio formats
- **Duration**: 3-30 seconds (optimal: 5-10 seconds)
- **Quality**: Clear speech, minimal background noise
- **Content**: Single speaker, natural speech
- **Size**: Maximum 50MB

### Example Request

```bash
curl -X POST "https://api.runpod.ai/v2/{endpoint-id}/runsync" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {api-key}" \
  -d '{
    "input": {
      "endpoint": "upload",
      "voice_file_url": "https://example.com/my-voice-sample.wav",
      "voice_name": "john-voice.wav"
    }
  }'
```

### Example Response

```json
{
  "status": "Voice 'john-voice.wav' uploaded successfully",
  "message": "F5-TTS will automatically transcribe the reference audio"
}
```

## 📋 List Voices

List all uploaded voice files.

**Endpoint:** `POST /runsync`

### Request Format

```json
{
  "input": {
    "endpoint": "list_voices"
  }
}
```

### Response Format

```json
{
  "voices": [
    {
      "name": "sarah-voice.wav",
      "size": 1048576,
      "last_modified": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 1,
  "status": "success"
}
```

### Example Request

```bash
curl -X POST "https://api.runpod.ai/v2/{endpoint-id}/runsync" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {api-key}" \
  -d '{
    "input": {
      "endpoint": "list_voices"
    }
  }'
```

## ⚠️ Error Handling

### Error Response Format

```json
{
  "error": "Error description"
}
```

### Common Errors

| Error | Description | Solution |
|-------|-------------|----------|
| `Text input is required` | Missing or empty text field | Provide valid text input |
| `Failed to download voice file` | Voice file URL inaccessible | Check URL and file availability |
| `S3 not configured` | Missing S3 credentials | Configure S3 environment variables |
| `F5-TTS inference failed` | Model processing error | Check text content and voice file |
| `Failed to upload generated audio to S3` | S3 upload failed | Verify S3 permissions and connectivity |

### Example Error Response

```json
{
  "error": "Text input is required"
}
```

## 🚀 Performance Characteristics

### Timing Benchmarks

| Operation | Cold Start | Warm Start | Notes |
|-----------|------------|-------------|-------|
| Model Loading | ~2-3 seconds | ~0.1 seconds | Pre-loaded in container |
| TTS Generation | ~1-2 seconds | ~0.5-1 seconds | Per 10 words |
| Voice Download | ~0.5-2 seconds | N/A | Depends on file size |
| S3 Upload | ~0.2-1 seconds | N/A | Depends on audio length |

### Resource Usage

- **GPU Memory**: 4-6GB (F5-TTS model)
- **CPU**: 2-4 cores recommended
- **Storage**: 10-20GB for models (build-time)
- **Network**: High bandwidth for S3 operations

## 🔧 Configuration

### Environment Variables

Configure your RunPod endpoint with these environment variables:

```bash
S3_BUCKET=your-s3-bucket-name
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=us-east-1
AWS_ENDPOINT_URL=https://s3.backblazeb2.com  # Optional for S3-compatible services
```

### S3 Bucket Setup

1. **Create S3 Bucket**: Create a bucket for storing voice files and generated audio
2. **Set Permissions**: Allow public read access for generated audio files
3. **Configure CORS**: Enable cross-origin requests if needed

Example bucket policy for public audio access:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-bucket-name/output/*"
    }
  ]
}
```

## 🧪 Testing & Development

### Local Testing

```bash
# Test with curl
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "This is a test of the local F5-TTS API."
    }
  }'
```

### Integration Testing

```python
import requests

def test_tts_generation():
    url = "https://api.runpod.ai/v2/your-endpoint/runsync"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer your-api-key"
    }
    data = {
        "input": {
            "text": "Hello, this is a test of the F5-TTS API.",
            "speed": 1.0
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    assert "audio_url" in result
    assert "duration" in result
    assert result["status"] == "completed"
    
    print(f"Generated audio: {result['audio_url']}")
    print(f"Duration: {result['duration']} seconds")

if __name__ == "__main__":
    test_tts_generation()
```

## 📈 Rate Limits & Scaling

### RunPod Serverless Limits

- **Concurrent Requests**: Scales automatically based on demand
- **Request Timeout**: 300 seconds maximum
- **Max Workers**: Configurable in RunPod dashboard
- **GPU Memory**: Shared among concurrent requests

### Best Practices

1. **Batch Processing**: Process multiple texts in sequence rather than parallel for memory efficiency
2. **Voice Caching**: Upload commonly used voices once, reuse multiple times
3. **Text Optimization**: Break very long texts into smaller chunks
4. **Error Handling**: Implement retry logic for transient failures

## 🔒 Security Considerations

### API Security

- **Authentication**: Use RunPod API keys for authentication
- **HTTPS**: All requests encrypted in transit
- **Input Validation**: Text and voice inputs are validated
- **Output Sanitization**: Generated files are safe for public access

### Data Privacy

- **Temporary Storage**: Voice files and generated audio are temporary
- **S3 Encryption**: Enable S3 server-side encryption for sensitive content
- **Access Control**: Configure S3 bucket permissions appropriately
- **Audit Logging**: Monitor API usage through RunPod dashboard

## 📚 SDK Examples

### Python SDK

```python
import runpod

# Configure API key
runpod.api_key = "your-runpod-api-key"

# Create endpoint
endpoint = runpod.Endpoint("your-endpoint-id")

# Generate TTS
response = endpoint.run_sync({
    "text": "Hello, world! This is F5-TTS in action.",
    "local_voice": "custom-voice.wav"
})

print(f"Audio URL: {response['audio_url']}")
print(f"Duration: {response['duration']} seconds")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function generateTTS(text, voiceFile = null) {
    const response = await axios.post(
        'https://api.runpod.ai/v2/your-endpoint/runsync',
        {
            input: {
                text: text,
                local_voice: voiceFile,
                speed: 1.0
            }
        },
        {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer your-api-key'
            }
        }
    );
    
    return response.data;
}

// Usage
generateTTS("Hello from JavaScript!")
    .then(result => {
        console.log(`Audio URL: ${result.audio_url}`);
        console.log(`Duration: ${result.duration} seconds`);
    })
    .catch(error => {
        console.error('Error:', error.response.data);
    });
```

---

**🎯 Ready to build amazing TTS applications with F5-TTS serverless!**