# S3 Bucket Directory Structure

This document defines the standardized S3 bucket structure for the F5-TTS RunPod deployment.

## Overview

The S3 bucket is organized into distinct directories for different types of data, enabling efficient storage, retrieval, and management of voice models, outputs, and cached resources.

## Directory Structure

```
s3://[BUCKET_NAME]/
├── voices/                 # Voice models and reference text files
│   ├── voice1.wav         # Audio reference file for voice cloning
│   ├── voice1.txt         # Corresponding reference text (required)
│   ├── voice2.wav
│   ├── voice2.txt
│   └── ...
├── output/                 # Generated TTS audio files  
│   ├── [job-uuid-1].wav   # TTS generation output
│   ├── [job-uuid-2].wav
│   └── ...
└── models/                 # Cached HuggingFace models (optional)
    ├── hub/               # HuggingFace Hub cache
    ├── torch/             # PyTorch model cache
    └── f5-tts/            # F5-TTS specific models
```

## Directory Details

### `/voices/` - Voice Models Storage

**Purpose**: Stores voice reference files and their corresponding text transcriptions for F5-TTS voice cloning.

**File Patterns**:
- `*.wav` - Audio reference files (typically 10-30 seconds of clean speech)
- `*.txt` - Reference text files (exact transcription of the audio)

**Naming Convention**:
- Voice files: `{voice_name}.wav`
- Text files: `{voice_name}.txt` (must match the voice filename)

**Requirements**:
- Each `.wav` file MUST have a corresponding `.txt` file
- Audio files should be high-quality WAV format (22kHz+ sample rate recommended)
- Text files must contain exact transcription of the audio content
- UTF-8 encoding for text files

**Example**:
```
voices/
├── john_doe.wav          # 15-second audio sample
├── john_doe.txt          # "Hello, this is John speaking clearly."
├── sarah_narrator.wav    # Professional narrator sample
└── sarah_narrator.txt    # "This is a sample of clear speech."
```

### `/output/` - Generated Audio Files

**Purpose**: Stores TTS generation results from processing requests.

**File Patterns**:
- `*.wav` - Generated audio files

**Naming Convention**:
- Format: `{job_uuid}.wav`
- Example: `123e4567-e89b-12d3-a456-426614174000.wav`

**Lifecycle**:
- Files are created upon successful TTS generation
- Accessible via signed URLs returned in API responses
- Retention policy depends on S3 bucket configuration

### `/models/` - Model Cache (Optional)

**Purpose**: Persistent storage for HuggingFace and PyTorch models to avoid re-downloading.

**Subdirectories**:
- `hub/` - HuggingFace Hub cache (controlled by `HF_HUB_CACHE`)
- `torch/` - PyTorch model cache (controlled by `TORCH_HOME`)
- `f5-tts/` - F5-TTS specific model files

**Benefits**:
- Faster startup times for RunPod instances
- Reduced bandwidth usage
- Consistent model versions across deployments

**Note**: This directory is managed automatically by the model caching system.

## API Integration

### Upload Endpoint
When uploading voice models via the API, files are automatically organized:

```json
{
  "input": {
    "endpoint": "upload",
    "voice_name": "my_voice.wav",
    "voice_file_url": "https://example.com/audio.wav",
    "reference_text": "This is the exact text spoken in the audio file."
  }
}
```

**Result**:
- `voices/my_voice.wav` - Audio file
- `voices/my_voice.txt` - Text file

### List Voices Endpoint
Retrieve available voices with metadata:

```json
{
  "input": {
    "endpoint": "list_voices"
  }
}
```

**Response**:
```json
{
  "voices": [
    {
      "voice_file": "my_voice.wav",
      "text_file": "my_voice.txt",
      "size": 245760,
      "last_modified": "2024-01-15T10:30:00Z"
    }
  ],
  "count": 1,
  "status": "success"
}
```

### TTS Generation
Reference voices by filename:

```json
{
  "input": {
    "text": "Generate this speech with my custom voice.",
    "local_voice": "my_voice.wav",
    "speed": 1.0
  }
}
```

**Process**:
1. Downloads `voices/my_voice.wav` and `voices/my_voice.txt`
2. Uses both files for high-quality voice cloning
3. Saves result to `output/{job_uuid}.wav`

## Best Practices

### Voice Quality
- Use high-quality audio recordings (minimal background noise)
- Ensure clear pronunciation and consistent speaking pace
- Keep reference audio between 10-30 seconds
- Use consistent audio format (WAV, 22kHz+ sample rate)

### File Management
- Use descriptive, consistent naming conventions
- Include speaker information in filenames where appropriate
- Maintain exact text transcriptions for optimal quality
- Regular cleanup of old output files to manage storage costs

### Security
- Implement appropriate S3 bucket policies
- Use signed URLs for secure file access
- Consider encryption for sensitive voice data
- Regular backup of voice model collections

## Troubleshooting

### Common Issues

**Missing Reference Text**:
- Symptom: Poor voice cloning quality
- Solution: Ensure every `.wav` file has a matching `.txt` file

**File Not Found Errors**:
- Check S3 bucket permissions
- Verify file names match exactly (case-sensitive)
- Confirm S3 credentials are properly configured

**Upload Failures**:
- Verify S3 bucket exists and is accessible
- Check file size limits and network connectivity
- Ensure proper content-type headers for audio files

### Monitoring
- Monitor S3 storage usage and costs
- Track upload/download success rates
- Review voice model usage patterns
- Set up alerts for storage capacity and access patterns