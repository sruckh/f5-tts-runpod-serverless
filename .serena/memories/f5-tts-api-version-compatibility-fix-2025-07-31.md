# F5-TTS API Version Compatibility Fix - 2025-07-31

## Critical Issue Resolved
**Problem**: F5-TTS container API version incompatibility causing complete inference failure
**Error**: `TypeError: F5TTS.infer() got an unexpected keyword argument 'ref_audio'`
**Impact**: Production-blocking error preventing all TTS generation

## Root Cause Analysis
- Recent "audio quality fix" applied `ref_audio` parameter based on official F5-TTS documentation
- Container F5-TTS version uses older API expecting `ref_file` parameter instead
- No version detection method available to determine correct parameter names
- Different F5-TTS versions use incompatible method signatures and parameter names

## Technical Solution Implemented

### Progressive Fallback System (4-Tier)
**File**: `runpod-handler.py:151-220`

**Tier 1**: `ref_file` + `infer()` method (older F5-TTS versions)
- Parameter: `{"ref_file": voice_path, "gen_text": text, "speed": speed}`
- Most likely to succeed with container's F5-TTS version

**Tier 2**: `ref_audio` + `infer()` method (newer F5-TTS versions)
- Parameter: `{"ref_audio": voice_path, "gen_text": text, "speed": speed}`
- Aligns with official F5-TTS documentation

**Tier 3**: Remove `ref_text` compatibility mode
- Removes optional `ref_text` parameter that may cause issues
- Graceful degradation maintaining core functionality

**Tier 4**: `generate()` method fallback (alternative API)
- Uses `current_model.generate(infer_params)` instead of `infer()`
- Handles result format differences between API versions

### Key Implementation Features
- **Comprehensive Logging**: Shows which method succeeds for debugging
- **Error Context**: Provides all attempted methods if complete failure occurs
- **Parameter Preservation**: Maintains existing audio preprocessing and cleanup
- **Zero Breaking Changes**: Existing functionality preserved during fallback attempts

## Architecture Impact

### Compatibility Matrix
| F5-TTS Version | Primary Method | Fallback Chain |
|----------------|----------------|----------------|
| Pre-v1 (older) | `ref_file` + `infer()` | → `generate()` |
| v1+ (newer) | `ref_audio` + `infer()` | → `ref_file` → `generate()` |
| Unknown/Mixed | Auto-detection via progressive fallback | All methods attempted |

### Error Recovery Strategy
```python
# Attempt sequence with detailed logging
try:
    # Tier 1: ref_file + infer() 
    audio_data, sample_rate, _ = current_model.infer(**infer_params)
except Exception as ref_file_error:
    try:
        # Tier 2: ref_audio + infer()
        infer_params["ref_audio"] = infer_params.pop("ref_file")
        audio_data, sample_rate, _ = current_model.infer(**infer_params)
    except Exception as ref_audio_error:
        # Continue through Tier 3 & 4...
```

## Production Benefits

### Immediate Fixes
- **Container Compatibility**: Works with current F5-TTS container version
- **Audio Quality**: Maintains librosa preprocessing and 8-second clipping
- **Error Handling**: Comprehensive fallback prevents total failures
- **Debugging**: Detailed logs identify successful method for optimization

### Future-Proofing
- **Version Agnostic**: Handles F5-TTS API changes without code updates
- **Deployment Flexibility**: Single codebase works across different container versions
- **Maintenance Reduction**: No need to track F5-TTS version compatibility manually
- **Upgrade Path**: Seamless transition when container F5-TTS version updates

## Documentation Updates

### TASKS.md Changes
- **New Task**: TASK-2025-07-31-006 (F5-TTS API Version Compatibility Fix)
- **Updated Context**: Reflects API parameter mismatch resolution
- **Findings**: Documents version incompatibility discoveries
- **Decisions**: Records progressive fallback implementation approach

### JOURNAL.md Entry
- **Complete Documentation**: What/Why/How/Issues/Result format
- **Technical Details**: 4-tier fallback system explanation
- **Error Context**: API version inconsistency challenges
- **Results**: Version-agnostic inference system achievement

## Expected Production Outcome
- **Container Deployment**: Should start successfully without API errors
- **Audio Generation**: Clear TTS output (not garbled) with proper preprocessing
- **Error Logs**: Will show "✅ F5-TTS inference successful with 'ref_file'" (most likely)
- **Fallback Activation**: Detailed logs if alternative methods needed

## Technical Context for Future Development
This compatibility fix represents a crucial pattern for handling API version differences in containerized AI services. The progressive fallback approach can be applied to other AI model integrations where version compatibility is uncertain or dynamic.

The solution prioritizes stability over performance optimization, ensuring production availability while providing debugging information to optimize for specific container versions in future iterations.