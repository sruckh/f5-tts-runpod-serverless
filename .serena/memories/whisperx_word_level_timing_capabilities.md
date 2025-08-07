# WhisperX Word-Level Timing Capabilities

## Overview
WhisperX is an enhanced version of OpenAI's Whisper that provides accurate word-level timestamps through forced alignment - a key capability that standard Whisper lacks.

## Core Technical Implementation

### Forced Alignment Process
- Uses wav2vec2 alignment models to align orthographic transcriptions with audio
- Provides phone-level segmentation for precise word-level timestamps
- Automatic language-based model selection for alignment

### Key API Pattern
```python
# 1. Transcribe audio
model = whisperx.load_model("large-v2", device, compute_type=compute_type)
result = model.transcribe(audio, batch_size=batch_size)

# 2. Perform forced alignment for word-level timing
model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
```

## Language Support
Tested default alignment models available for:
- English (en), French (fr), German (de), Spanish (es)
- Italian (it), Japanese (ja), Chinese (zh), Dutch (nl)
- Custom phoneme-based ASR models can be used for other languages

## Key Features

### Word-Level Timing Options
- Standard word-level timestamps via forced alignment
- Character-level alignments available with `return_char_alignments=True`
- Word highlighting in SRT output with `--highlight_words True`
- Integration with speaker diarization for speaker-attributed word timing

### Performance Characteristics
- Up to 70x realtime transcription speed with faster-whisper backend
- Batched inference capability for long audio files
- Minimal overhead for alignment step compared to transcription
- GPU memory optimization options available

### Output Applications
- Accurate subtitle generation with word-level precision
- Word-synchronized audio/video editing
- Speaker-attributed transcripts at word level
- Real-time transcription with precise timing

## CLI Usage Patterns
```bash
# Basic word timing
whisperx audio.wav --highlight_words True

# With speaker diarization + word timing
whisperx audio.wav --model large-v2 --diarize --highlight_words True

# Language-specific with larger model
whisperx --model large-v2 --language de audio.wav --highlight_words True
```

## Integration Considerations
- Requires separate alignment model loading after transcription
- Can be combined with speaker diarization for multi-speaker word timing
- Supports both Python API and CLI interfaces
- Memory management needed for GPU usage (model cleanup)

## Project Context
This information is relevant for F5-TTS integration where precise word-level timing extraction may be needed for subtitle generation, audio synchronization, or speech synthesis alignment tasks.