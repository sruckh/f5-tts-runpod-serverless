# F5-TTS RunPod Serverless API Reference

This document provides the actual API reference for the F5-TTS RunPod Serverless implementation.

## Base Endpoint

All requests are made to your RunPod serverless endpoint URL:
```
POST https://api.runpod.ai/v2/{endpoint_id}/runsync
```

## API Overview

The F5-TTS API is a **synchronous** serverless function that supports:
- **TTS Generation**: Convert text to speech using custom voices (returns results immediately)
- **Word-Level Timing**: Generate precise timing data for subtitles and FFMPEG integration
- **Voice Upload**: Upload custom voice models via URL
- **Voice Management**: List available uploaded voices
- **File Download**: Download generated audio files and timing data via direct S3 URLs

**Important**: This is a synchronous API - no job queuing, no status checking, results returned immediately.

## Endpoints

### 1. TTS Generation (Default)

Generate text-to-speech audio using uploaded voice models. Returns results immediately.

**Request**
```json
{
  "input": {
    "text": "I am a puppet, and the digital world owns me!",
    "speed": 0.9,
    "local_voice": "Kurt_12s.wav",
    "return_word_timings": true,
    "timing_format": "srt"
  }
}
```

**Parameters**:
- `text` (string, required): Text to convert to speech
- `speed` (float, optional): Speech speed multiplier (default: 1.0)
- `local_voice` (string, optional): Voice filename from S3 voices/ directory
- `return_word_timings` (boolean, optional): Generate word-level timing data (default: false)
- `timing_format` (string, optional): Timing format preference: "srt", "vtt", "csv", "json", "ass" (default: "srt")

**Response** (Immediate - Synchronous)
```json
{
  "audio_url": "https://s3.us-west-001.backblazeb2.com/s3f5tts/output/dacf3df8-e5c3-4a37-b7da-1acf5cd214df.wav",
  "duration": 2.7413333333333334,
  "job_id": "dacf3df8-e5c3-4a37-b7da-1acf5cd214df",
  "status": "completed",
  "text": "I am a puppet, and the digital world owns me!",
  "timing_files": {
    "srt": "/download?job_id=dacf3df8-e5c3-4a37-b7da-1acf5cd214df&type=timing&format=srt",
    "vtt": "/download?job_id=dacf3df8-e5c3-4a37-b7da-1acf5cd214df&type=timing&format=vtt",
    "csv": "/download?job_id=dacf3df8-e5c3-4a37-b7da-1acf5cd214df&type=timing&format=csv",
    "json": "/download?job_id=dacf3df8-e5c3-4a37-b7da-1acf5cd214df&type=timing&format=json",
    "ass": "/download?job_id=dacf3df8-e5c3-4a37-b7da-1acf5cd214df&type=timing&format=ass"
  },
  "timing_format": "srt",
  "word_count": 11,
  "timing_confidence": 0.95
}
```

**Timing Features**:
- ✅ **Word-level timing data** - Generated with Google Cloud Speech-to-Text API
- ✅ **Multiple formats** - SRT, VTT, CSV, JSON, ASS (optimized for FFMPEG)
- ✅ **FFMPEG integration** - ASS format provides advanced subtitle styling
- ✅ **Social media ready** - Perfect for video content with word-by-word subtitles
- ✅ **Nanosecond precision** - Enterprise-grade timing accuracy with confidence scoring
- ✅ **Automatic punctuation** - Enhanced readability in subtitle formats
- 💰 **Cost**: ~$0.012 per request when `return_word_timings: true`

**Google Speech API Integration**:
- **Model**: `latest_long` model optimized for accuracy
- **Sample Rate**: Automatically configured for 24kHz F5-TTS audio compatibility
- **Features**: Automatic punctuation, confidence scoring, word-level timestamps
- **Processing Time**: Additional 2-4 seconds for timing extraction
- **Accuracy**: Enterprise-grade timing precision with confidence scores typically >0.90

### 2. Upload Voice Model

Upload a voice model via URL. F5-TTS automatically transcribes the reference audio.

**Request**
```json
{
  "input": {
    "endpoint": "upload",
    "voice_name": "john_speaker.wav",
    "voice_file_url": "https://example.com/audio.wav"
  }
}
```

**Parameters**:
- `endpoint` (string): Must be "upload"
- `voice_name` (string, required): Voice filename (must end with .wav)
- `voice_file_url` (string, required): URL to download voice file

**Response**
```json
{
  "status": "Voice 'john_speaker.wav' uploaded successfully",
  "message": "F5-TTS will automatically transcribe the reference audio"
}
```

**Error Response**
```json
{
  "error": "voice_file_url is required for upload"
}
```

**Note**: ❌ **No reference text required** - F5-TTS automatically transcribes uploaded audio.

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
      "name": "john_speaker.wav",
      "size": 245760,
      "last_modified": "2024-01-15T10:30:00Z"
    },
    {
      "name": "sarah_narrator.wav",
      "size": 189432,
      "last_modified": "2024-01-14T15:22:00Z"
    }
  ],
  "count": 2,
  "status": "success"
}
```

### 4. Download Files (Audio & Timing)

Download generated audio files and timing data via direct S3 URLs (no base64 encoding).

#### Download Audio File (Default)

**Request**
```json
{
  "input": {
    "endpoint": "download",
    "job_id": "dacf3df8-e5c3-4a37-b7da-1acf5cd214df"
  }
}
```

**Response**
```json
{
  "audio_url": "https://s3.us-west-001.backblazeb2.com/s3f5tts/output/dacf3df8-e5c3-4a37-b7da-1acf5cd214df.wav",
  "content_type": "audio/wav",
  "filename": "dacf3df8-e5c3-4a37-b7da-1acf5cd214df.wav",
  "status": "ready"
}
```

#### Download Timing Files

**Request**
```json
{
  "input": {
    "endpoint": "download",
    "job_id": "dacf3df8-e5c3-4a37-b7da-1acf5cd214df",
    "type": "timing",
    "format": "srt"
  }
}
```

**Response**
```json
{
  "timing_url": "https://s3.us-west-001.backblazeb2.com/s3f5tts/timings/dacf3df8-e5c3-4a37-b7da-1acf5cd214df.srt",
  "content_type": "text/plain",
  "format": "srt",
  "filename": "dacf3df8-e5c3-4a37-b7da-1acf5cd214df.srt",
  "status": "ready"
}
```

**Parameters**:
- `endpoint` (string): Must be "download"
- `job_id` (string, required): Job ID from TTS generation response
- `type` (string, optional): "audio" (default) or "timing"
- `format` (string, optional): For timing files: "srt", "vtt", "csv", "json", "ass"

**Supported Timing Formats**:
- **SRT**: SubRip format for basic subtitles
- **VTT**: WebVTT format for web video
- **CSV**: Comma-separated values for data processing
- **JSON**: Structured data with full timing metadata
- **ASS**: Advanced SubStation Alpha for FFMPEG styling

## Example Workflows

### TTS Generation with Word Timings

Generate TTS with word-level timing data for FFMPEG subtitle integration:

```json
{
  "input": {
    "text": "Hello world, this is a test of the timing system.",
    "return_word_timings": true,
    "timing_format": "ass",
    "local_voice": "narrator.wav"
  }
}
```

**Response**:
```json
{
  "audio_url": "https://s3.us-west-001.backblazeb2.com/s3f5tts/output/12345.wav",
  "duration": 3.2,
  "job_id": "12345",
  "status": "completed",
  "text": "Hello world, this is a test of the timing system.",
  "timing_files": {
    "srt": "/download?job_id=12345&type=timing&format=srt",
    "vtt": "/download?job_id=12345&type=timing&format=vtt",
    "csv": "/download?job_id=12345&type=timing&format=csv",
    "json": "/download?job_id=12345&type=timing&format=json",
    "ass": "/download?job_id=12345&type=timing&format=ass"
  },
  "timing_format": "ass",
  "word_count": 10,
  "timing_confidence": 0.94
}
```

**FFMPEG Integration**:
```bash
# Get timing file URL from download endpoint
timing_url=$(
curl -X POST "https://api.runpod.ai/v2/{endpoint_id}/runsync" \
  -H "Content-Type: application/json" \
  -d '{"input": {"endpoint": "download", "job_id": "12345", "type": "timing", "format": "ass"}}' \
  | jq -r '.timing_url')

# Download subtitle file directly from S3
curl "$timing_url" -o subtitles.ass

# Overlay subtitles on video
ffmpeg -i video.mp4 -vf "ass=subtitles.ass" output_with_subtitles.mp4
```

### Basic TTS Generation
```json
{
  "input": {
    "text": "I am a puppet, and the digital world owns me!",
    "speed": 0.9,
    "local_voice": "Kurt_12s.wav"
  }
}
```

**Response** (immediate):
```json
{
  "audio_url": "https://s3.us-west-001.backblazeb2.com/s3f5tts/output/dacf3df8-e5c3-4a37-b7da-1acf5cd214df.wav",
  "duration": 2.7413333333333334,
  "job_id": "dacf3df8-e5c3-4a37-b7da-1acf5cd214df",
  "status": "completed",
  "text": "I am a puppet, and the digital world owns me!"
}
```

### Custom Voice Upload and Use
1. **Upload voice**:
```json
{
  "input": {
    "endpoint": "upload",
    "voice_name": "my_voice.wav",
    "voice_file_url": "https://example.com/voice_sample.wav"
  }
}
```

2. **Use uploaded voice**:
```json
{
  "input": {
    "text": "Hello from my custom voice!",
    "local_voice": "my_voice.wav"
  }
}
```

### Download Audio File
```json
{
  "input": {
    "endpoint": "download",
    "job_id": "dacf3df8-e5c3-4a37-b7da-1acf5cd214df"
  }
}
```

**Response**:
```json
{
  "audio_url": "https://s3.us-west-001.backblazeb2.com/s3f5tts/output/dacf3df8-e5c3-4a37-b7da-1acf5cd214df.wav",
  "content_type": "audio/wav",
  "filename": "dacf3df8-e5c3-4a37-b7da-1acf5cd214df.wav",
  "status": "ready"
}
```

**Download WAV file directly from S3**:
```bash
# Get audio URL from download response
audio_url=$(curl -X POST "https://api.runpod.ai/v2/{endpoint_id}/runsync" \
  -H "Content-Type: application/json" \
  -d '{"input": {"endpoint": "download", "job_id": "dacf3df8-e5c3-4a37-b7da-1acf5cd214df"}}' \
  | jq -r '.audio_url')

# Download audio file directly from S3
curl "$audio_url" -o output.wav
```

## Best Practices

### Voice Upload
- Use high-quality WAV files (22kHz+ sample rate recommended)
- **Optimal length**: 3-10 seconds for best voice cloning quality
- Clear speech without background noise
- Use descriptive, consistent naming conventions
- **No reference text needed** - F5-TTS automatically transcribes

### TTS Generation  
- Test voice quality with short text samples first
- Use appropriate speed settings (0.5-2.0 range)
- **Synchronous processing** - results returned immediately
- Monitor S3 storage usage for generated files

### Error Recovery
- Implement retry logic for network timeouts
- Validate input parameters before submission
- Handle S3 access errors gracefully
- Check voice file availability before TTS generation
