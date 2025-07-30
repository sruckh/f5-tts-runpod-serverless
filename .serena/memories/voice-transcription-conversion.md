# F5-TTS Voice Transcription Format Conversion

**Date**: 2025-07-30 12:00  
**Task**: TASK-2025-07-30-001  
**Context**: Voice model preparation for F5-TTS deployment

## Summary
Successfully converted 5 voice model transcriptions from SRT/CSV formats to F5-TTS compatible plain text files, enabling proper voice cloning functionality.

## Technical Details

### Problem
- F5-TTS requires simple `.txt` reference files containing exact transcription text
- User provided voice models with transcriptions in SRT (subtitle) and CSV (timestamped) formats
- Need automated conversion preserving text quality while removing timing data

### Solution
- **Conversion Script**: `convert_transcriptions.py` with dual format parsers
- **SRT Parser**: Extracts subtitle text, skips sequence numbers and timestamps
- **CSV Parser**: Reads segment column, handles quotes and formatting
- **File Matching**: Generates `.txt` files matching voice file names

### Voice Models Processed
- **Dorota**: 2043 characters from Dorota.srt
- **Elijah**: 799 characters from Elijah.srt  
- **Kim**: 523 characters from Kim.srt
- **Kurt**: 4029 characters from Kurt.srt
- **Scott**: 1012 characters from Scott.srt

### Files Created
- `convert_transcriptions.py` - Reusable conversion automation
- `Voices/*.txt` - F5-TTS reference text files (5 files)
- `.gitignore` - Privacy protection for voice data

### Key Findings
- F5-TTS voice cloning quality depends on accurate reference text
- SRT format more reliable than CSV for text extraction
- Voice files should be excluded from repository for privacy
- Automation enables easy addition of future voice models

## Impact
Voice models now ready for F5-TTS training with proper reference text format, enabling high-quality voice cloning deployment.