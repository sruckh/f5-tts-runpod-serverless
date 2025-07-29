# F5-TTS RunPod Serverless API Reference

This document provides a comprehensive reference for the F5-TTS RunPod Serverless API.

## Base Endpoint

All requests are made to your RunPod serverless endpoint URL:
```
POST https://api.runpod.ai/v2/{endpoint_id}/runsync
```

## API Overview

The F5-TTS API supports the following operations:
- **TTS Generation**: Convert text to speech using custom voices
- **Voice Upload**: Upload custom voice models with reference text
- **Voice Management**: List and manage available voices
- **Job Management**: Check status and retrieve results

## Endpoints

### 1. TTS Generation (Default)

Generate text-to-speech audio using uploaded voice models.

**Request**
```json
{
  "input": {
    "text": "Hello, world! This is a test of F5-TTS voice synthesis.",
    "speed": 1.0,
    "return_word_timings": true,
    "local_voice": "my-voice.wav"
  }
}
```

**Parameters**:
- `text` (string, required): Text to convert to speech
- `speed` (float, optional): Speech speed multiplier (default: 1.0)
- `return_word_timings` (boolean, optional): Include word-level timestamps (default: true)
- `local_voice` (string, optional): Voice filename from S3 voices/ directory or URL

**Response**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "QUEUED"
}
```

### 2. Upload Voice Model

Upload a voice model with its reference audio and text for high-quality voice cloning.

**Request**
```json
{
  "input": {
    "endpoint": "upload",
    "voice_name": "john_speaker.wav",
    "voice_file_url": "https://example.com/audio.wav",
    "reference_text": "This is the exact text spoken in the reference audio file."
  }
}
```

**Parameters**:
- `endpoint` (string): Must be "upload"
- `voice_name` (string, required): Voice filename (must end with .wav)
- **Voice File** (one required):
  - `voice_file_url` (string): URL to download voice file (recommended)
  - `voice_file` (string): Base64-encoded voice file (deprecated)
- **Reference Text** (one required):
  - `reference_text` (string): Direct text transcription (recommended)
  - `text_file_url` (string): URL to download text file
  - `text_file` (string): Base64-encoded text file (deprecated)

**Response**
```json
{
  "status": "Voice 'john_speaker.wav' and reference text uploaded successfully."
}
```

**Error Response**
```json
{
  "error": "Reference text is required. Provide reference_text, text_file_url, or text_file."
}
```

### 3. List Available Voices

Retrieve a list of all uploaded voice models.

**Request**
```json
{
  "input": {
    "endpoint": "list_voices"
  }
}
```

**Response**
```json
{
  "voices": [
    {
      "voice_file": "john_speaker.wav",
      "text_file": "john_speaker.txt",
      "size": 245760,
      "last_modified": "2024-01-15T10:30:00Z"
    },
    {
      "voice_file": "sarah_narrator.wav", 
      "text_file": "sarah_narrator.txt",
      "size": 189432,
      "last_modified": "2024-01-14T15:22:00Z"
    }
  ],
  "count": 2,
  "status": "success"
}
```

### 4. Job Status

Check the processing status of a TTS generation job.

**Request**
```json
{
  "input": {
    "endpoint": "status",
    "job_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

**Response**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "COMPLETED"
}
```

**Status Values**:
- `QUEUED`: Job is waiting to be processed
- `PROCESSING`: Job is currently being processed
- `COMPLETED`: Job finished successfully
- `ERROR`: Job failed with an error

### 5. Get Result

Retrieve the generated audio and metadata for a completed job.

**Request**
```json
{
  "input": {
    "endpoint": "result",
    "job_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

**Response**
```json
{
  "audio_url": "https://your-bucket.s3.us-east-1.amazonaws.com/output/123e4567-e89b-12d3-a456-426614174000.wav",
  "word_timings": [
    {
      "word": "Hello,",
      "start_time": 0.0,
      "end_time": 0.4
    },
    {
      "word": "world!",
      "start_time": 0.45,
      "end_time": 0.9
    }
  ],
  "duration": 2.5
}
```

**Error Response**
```json
{
  "error": "Job is not complete. Status: PROCESSING"
}
```

## Example Workflows

### Basic TTS Generation

1. **Generate Speech** (without custom voice):
```json
{
  "input": {
    "text": "Hello, this is a test of the default voice.",
    "speed": 1.0
  }
}
```

2. **Check Status**:
```json
{
  "input": {
    "endpoint": "status", 
    "job_id": "your-job-id"
  }
}
```

3. **Get Result**:
```json
{
  "input": {
    "endpoint": "result",
    "job_id": "your-job-id" 
  }
}
```

### Custom Voice Cloning

1. **Upload Voice Model**:
```json
{
  "input": {
    "endpoint": "upload",
    "voice_name": "custom_speaker.wav",
    "voice_file_url": "https://example.com/speaker_sample.wav",
    "reference_text": "This is a clear sample of the speaker's voice."
  }
}
```

2. **Generate with Custom Voice**:
```json
{
  "input": {
    "text": "Now generating speech with the custom voice model.",
    "local_voice": "custom_speaker.wav",
    "speed": 1.0
  }
}
```

3. **Check Available Voices**:
```json
{
  "input": {
    "endpoint": "list_voices"
  }
}
```

## Error Handling

All endpoints return appropriate HTTP status codes and error messages:

**Common Error Responses**:
```json
{
  "error": "Text input is required."
}
```

```json
{
  "error": "Invalid job_id."
}
```

```json
{
  "error": "Failed to download voice: connection timeout"
}
```

## Rate Limits and Constraints

- **Text Length**: Maximum 1000 characters per request
- **Audio Files**: WAV format recommended, maximum file size 50MB
- **Concurrent Jobs**: Up to 10 concurrent TTS generations per endpoint
- **Storage**: Generated audio files are retained for 7 days

## Best Practices

### Voice Upload
- Use high-quality WAV files (22kHz+ sample rate)
- Keep reference audio between 10-30 seconds
- Ensure reference text exactly matches the spoken audio
- Use descriptive, consistent naming conventions

### TTS Generation  
- Test voice quality with short text samples first
- Use appropriate speed settings (0.5-2.0 range)
- Monitor job status for long generations
- Cache frequently used audio results

### Error Recovery
- Implement retry logic for network timeouts
- Check job status periodically for long-running tasks
- Validate input parameters before submission
- Handle S3 access errors gracefully
