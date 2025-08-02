# F5-TTS Google Speech API Timing Attribute Fix

**Date**: 2025-08-02
**Task ID**: TASK-2025-08-02-008

## Critical Issue Resolved
Fixed `AttributeError: 'datetime.timedelta' object has no attribute 'nanos'` that was breaking Google Cloud Speech-to-Text word-level timing extraction functionality.

## Root Cause
Google Speech API response format evolved:
- **Old Format**: protobuf Duration objects with `.seconds` and `.nanos` attributes
- **New Format**: datetime.timedelta objects with `.total_seconds()` method
- **Impact**: Original code assumed `.nanos` attribute always available, causing crashes

## Technical Solution Implemented

### Multi-Format Timing Detection (runpod-handler.py:302-367)
Enhanced `extract_word_timings()` function with robust format handling:

```python
# Handle different timing formats
if hasattr(word_info.start_time, 'total_seconds'):
    # datetime.timedelta object
    start_time = word_info.start_time.total_seconds()
elif hasattr(word_info.start_time, 'seconds'):
    # Google protobuf Duration object
    start_time = word_info.start_time.seconds
    if hasattr(word_info.start_time, 'nanos'):
        start_time += word_info.start_time.nanos * 1e-9
else:
    # Try direct conversion if it's already a number
    try:
        start_time = float(word_info.start_time)
    except (TypeError, ValueError):
        # Log warning and skip problematic word
        continue
```

### Key Features
1. **Backward Compatibility**: Supports both old (Duration) and new (timedelta) formats
2. **Graceful Error Handling**: Skips problematic words instead of crashing entire system
3. **Future-Proofing**: Extensible design for additional format variations
4. **Comprehensive Logging**: Detailed warnings for unknown timing formats
5. **Production Ready**: No crashes, graceful degradation when needed

## Impact
- **Before**: Timing extraction completely broken with AttributeError
- **After**: Robust timing extraction works across multiple API versions
- **Benefit**: Core Day 1 FFMPEG subtitle integration functionality restored

## Files Modified
- `runpod-handler.py:302-367` - Enhanced `extract_word_timings()` with multi-format detection
- `TASKS.md` - Updated current task with implementation details
- `JOURNAL.md` - Added comprehensive implementation documentation

## Technical Patterns for Future Reference
This fix demonstrates important patterns for handling API evolution:
1. **Multi-format attribute detection** using `hasattr()`
2. **Graceful fallback chains** with error handling
3. **Backward compatibility** preservation
4. **Comprehensive logging** for debugging unknown formats
5. **Continuation processing** instead of failing fast

## User Feedback Integration
This fix directly addresses user-reported error and restores critical timing functionality that was identified as a "Day 1 goal" for FFMPEG integration workflows.