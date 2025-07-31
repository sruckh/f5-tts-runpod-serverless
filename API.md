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

Generate text-to-speech audio using uploaded voice models with downloadable timing files.

**Request**
```json
{
  "input": {
    "text": "Hello, world! This is a test of F5-TTS voice synthesis.",
    "speed": 1.0,
    "return_word_timings": true,
    "timing_format": "srt",
    "local_voice": "my-voice.wav"
  }
}
```

**Parameters**:
- `text` (string, required): Text to convert to speech
- `speed` (float, optional): Speech speed multiplier (default: 1.0)
- `return_word_timings` (boolean, optional): Include word-level timestamps (default: true)
- `timing_format` (string, optional): Format for timing data - "srt", "vtt", "compact", "json" (default: "json")
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
    "text_file_url": "https://example.com/reference_text.txt"
  }
}
```

**Parameters**:
- `endpoint` (string): Must be "upload"
- `voice_name` (string, required): Voice filename (must end with .wav)
- **Voice File** (one required):
  - `voice_file_url` (string): URL to download voice file (recommended)
  - `voice_file` (string): Base64-encoded voice file (deprecated)
- **Reference Text File** (one required):
  - `text_file_url` (string): URL to download text file (recommended)
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
  "error": "Reference text file is required. Provide text_file_url or text_file."
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

Retrieve the generated audio and metadata for a completed job with secure downloads and timing files.

**Request**
```json
{
  "input": {
    "endpoint": "result",
    "job_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

**Response (timing_format: "srt")**
```json
{
  "audio_url": "/download?file_path=output/123e4567-e89b-12d3-a456-426614174000.wav",
  "duration": 2.5,
  "timing_files": {
    "srt": "/download?file_path=timings/123e4567-e89b-12d3-a456-426614174000.srt"
  },
  "timing_format": "srt"
}
```

**Response (timing_format: "json" - backwards compatible)**
```json
{
  "audio_url": "/download?file_path=output/123e4567-e89b-12d3-a456-426614174000.wav",
  "duration": 2.5,
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
  "timing_files": {
    "srt": "/download?file_path=timings/123e4567-e89b-12d3-a456-426614174000.srt",
    "compact": "/download?file_path=timings/123e4567-e89b-12d3-a456-426614174000.csv"
  },
  "timing_format": "json"
}
```

**Error Response**
```json
{
  "error": "Job is not complete. Status: PROCESSING"
}
```

### 6. Download Files

Download audio files or timing data securely through the serverless function.

**Request**
```json
{
  "input": {
    "endpoint": "download",
    "file_path": "output/123e4567-e89b-12d3-a456-426614174000.wav"
  }
}
```

**Parameters**:
- `endpoint` (string): Must be "download"
- `file_path` (string, required): Path to file (e.g., "output/job-id.wav", "timings/job-id.srt")

**Response**
```json
{
  "success": true,
  "file_content": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+Dx7VkxDDuC6+GxYxoFOYTW8dWAKAUu...",
  "mime_type": "audio/wav",
  "file_size": 245760,
  "file_name": "123e4567-e89b-12d3-a456-426614174000.wav"
}
```

**Details**
- **Auth**: Authentication handled by serverless function
- **Security**: Path sanitization prevents directory traversal attacks
- **Format**: Files returned as base64-encoded content with metadata
- **Notes**: Replaces direct S3 URLs for secure access control

## Timing Data Formats

### SRT Format (FFMPEG Compatible)
Perfect for video subtitles with one word per subtitle:
```
1
00:00:00,000 --> 00:00:00,480
Hello,

2
00:00:00,530 --> 00:00:01,010
world!
```

### VTT Format (WebVTT)
Alternative subtitle format:
```
WEBVTT

00:00:00.000 --> 00:00:00.480
Hello,

00:00:00.530 --> 00:00:01.010
world!
```

### Compact CSV Format
Lightweight format for custom processing:
```
word,start_time,end_time
Hello,0.000,0.480
world!,0.530,1.010
```

### JSON Format (Backwards Compatible)
Original format for legacy applications - included inline in result response.

## Example Workflows

### Basic TTS Generation with Timing Files

1. **Generate Speech with SRT timing**:
```json
{
  "input": {
    "text": "Hello, this is a test of the default voice.",
    "speed": 1.0,
    "timing_format": "srt",
    "return_word_timings": true
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

**Response**:
```json
{
  "audio_url": "/download?file_path=output/your-job-id.wav",
  "duration": 2.5,
  "timing_files": {
    "srt": "/download?file_path=timings/your-job-id.srt"
  },
  "timing_format": "srt"
}
```

4. **Download Audio File**:
```json
{
  "input": {
    "endpoint": "download",
    "file_path": "output/your-job-id.wav"
  }
}
```

5. **Download SRT Timing File**:
```json
{
  "input": {
    "endpoint": "download", 
    "file_path": "timings/your-job-id.srt"
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
    "text_file_url": "https://example.com/speaker_reference.txt"
  }
}
```

2. **Generate with Custom Voice**:
```json
{
  "input": {
    "text": "Now generating speech with the custom voice model.",
    "local_voice": "custom_speaker.wav",
    "speed": 1.0,
    "timing_format": "compact",
    "return_word_timings": true
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

### FFMPEG Video Integration

Perfect for creating social media videos with word-by-word subtitles:

1. **Generate TTS with SRT timing**:
```json
{
  "input": {
    "text": "Create amazing social media content with F5-TTS and FFMPEG integration.",
    "local_voice": "my_voice.wav",
    "timing_format": "srt"
  }
}
```

2. **Download files for FFMPEG**:
```bash
# Download audio
curl -X POST "https://api.runpod.ai/v2/{endpoint}/runsync" \
  -H "Content-Type: application/json" \
  -d '{"input":{"endpoint":"download","file_path":"output/job-id.wav"}}' \
  | jq -r '.file_content' | base64 -d > audio.wav

# Download SRT subtitles  
curl -X POST "https://api.runpod.ai/v2/{endpoint}/runsync" \
  -H "Content-Type: application/json" \
  -d '{"input":{"endpoint":"download","file_path":"timings/job-id.srt"}}' \
  | jq -r '.file_content' | base64 -d > subtitles.srt
```

3. **Create video with FFMPEG**:
```bash
# Social media video with word-by-word subtitles
ffmpeg -i audio.wav -f lavfi -i color=black:size=1080x1920:duration=10 \
  -vf "subtitles=subtitles.srt:force_style='Fontsize=36,PrimaryColour=&Hffffff,Alignment=2'" \
  -c:a copy -shortest social_media_video.mp4
```

### Multiple Format Example

Generate timing data in multiple formats for different use cases:

1. **Request JSON format** (gets multiple formats automatically):
```json
{
  "input": {
    "text": "This will generate multiple timing formats automatically.",
    "timing_format": "json"
  }
}
```

2. **Response includes multiple downloadable formats**:
```json
{
  "audio_url": "/download?file_path=output/job-id.wav",
  "duration": 3.2,
  "word_timings": [...],
  "timing_files": {
    "srt": "/download?file_path=timings/job-id.srt",
    "compact": "/download?file_path=timings/job-id.csv"
  },
  "timing_format": "json"
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
- **Optimal length**: 3-10 seconds (auto-clipped to 8s if longer for best quality)
- Ensure reference text exactly matches the spoken audio
- Use descriptive, consistent naming conventions
- Clear speech without background noise recommended

### TTS Generation  
- Test voice quality with short text samples first
- Use appropriate speed settings (0.5-2.0 range)
- Monitor job status for long generations
- Cache frequently used audio results

### Timing Data Formats
- **SRT**: Best for FFMPEG video integration and social media
- **CSV**: Ideal for custom processing and data analysis  
- **VTT**: Alternative to SRT for web-based applications
- **JSON**: Use for backwards compatibility or programmatic access
- Choose format based on your workflow - files reduce API payload by 80-90%

### Error Recovery
- Implement retry logic for network timeouts
- Check job status periodically for long-running tasks
- Validate input parameters before submission
- Handle S3 access errors gracefully
