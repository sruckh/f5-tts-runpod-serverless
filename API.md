# API Reference

This document provides a detailed reference for the F5-TTS RunPod Serverless API.

## Endpoints

### TTS Generation

**Request**
```json
{
  "input": {
    "text": "Hello, world! This is a test.",
    "speed": 1.0,
    "return_word_timings": true,
    "local_voice": "my-voice.wav" // or a URL to a voice file
  }
}
```

**Response**
```json
{
  "job_id": "<uuid>",
  "status": "QUEUED"
}
```

### Upload Voice Model

**Request**
```json
{
  "input": {
    "endpoint": "upload",
    "voice_name": "my-voice.wav",
    "file": "<base64_encoded_file>", // or "url_file": "<url_to_file>"
  }
}
```

**Response**
```json
{
  "status": "Voice 'my-voice.wav' uploaded successfully."
}
```

### Job Status

**Request**
```json
{
  "input": {
    "endpoint": "status",
    "job_id": "<uuid>"
  }
}
```

**Response**
```json
{
  "job_id": "<uuid>",
  "status": "COMPLETED" // or QUEUED, PROCESSING, ERROR
}
```

### Get Result

**Request**
```json
{
  "input": {
    "endpoint": "result",
    "job_id": "<uuid>"
  }
}
```

**Response**
```json
{
  "audio_url": "<s3_url_to_audio_file>",
  "word_timings": [
    {
      "word": "Hello,",
      "start_time": 0.0,
      "end_time": 0.4
    },
    ...
  ],
  "duration": 2.5
}
```
