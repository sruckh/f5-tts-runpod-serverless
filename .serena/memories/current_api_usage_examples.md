# F5-TTS RunPod API Usage Examples

## Base Endpoint
All requests go to your RunPod serverless endpoint:
```
POST https://api.runpod.ai/v2/{endpoint_id}/runsync
```

## 1. Generate TTS Audio
```bash
curl -X POST "https://api.runpod.ai/v2/{endpoint_id}/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "Hello, world! This is a test of F5-TTS voice synthesis.",
      "speed": 1.0,
      "return_word_timings": true,
      "local_voice": "my-voice.wav"
    }
  }'
```

## 2. Upload Custom Voice
```bash
curl -X POST "https://api.runpod.ai/v2/{endpoint_id}/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "endpoint": "upload",
      "voice_file_url": "https://example.com/voice.wav",
      "voice_name": "my-custom-voice.wav"
    }
  }'
```

## 3. Check Job Status
```bash
curl -X POST "https://api.runpod.ai/v2/{endpoint_id}/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "endpoint": "status",
      "job_id": "123e4567-e89b-12d3-a456-426614174000"
    }
  }'
```

## 4. Get Job Results
```bash
curl -X POST "https://api.runpod.ai/v2/{endpoint_id}/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "endpoint": "result",
      "job_id": "123e4567-e89b-12d3-a456-426614174000"
    }
  }'
```

## 5. List Available Voices
```bash
curl -X POST "https://api.runpod.ai/v2/{endpoint_id}/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "endpoint": "list_voices"
    }
  }'
```