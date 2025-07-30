# F5TTS API Compatibility Fix Memory

## Issue Context
- **Environment**: RunPod deployment with CUDA 12.4.0
- **Problem**: F5TTS model initialization failure due to API incompatibility
- **Error**: Model initialization and inference API parameter mismatches
- **Date**: 2025-07-30

## Root Cause
The F5TTS library API had breaking changes that weren't reflected in the runpod-handler.py implementation:
1. Model initialization parameter changes
2. Inference method parameter name changes  
3. Return value structure changes (tuple unpacking issues)

## Files Modified

### `/runpod-handler.py`

#### Lines 50-56: Model Initialization Fix
**Before:**
```python
model = F5TTS(
    model_type="F5-TTS",
    ckpt_file=model_path,
    vocab_file=vocab_path,
    device=device
)
```

**After:**
```python
model = F5TTS(
    model="F5-TTS",  # Changed: model_type → model
    ckpt_file=model_path,
    vocab_file=vocab_path,
    device=device,
    use_ema=True  # Added: EMA model usage
)
```

#### Lines 125-137: Inference Method Parameter Fix
**Before:**
```python
audio, sample_rate = model.sample(
    text=text,
    ref_audio=ref_audio_path,
    ref_text=ref_text,
    target_sample_rate=target_sample_rate,
    nfe_step=nfe_step,
    cfg_strength=cfg_strength,
    sway_sampling_coef=sway_sampling_coef,
    speed=speed,
    fix_duration=fix_duration
)
```

**After:**
```python
generated_audio = model.sample(
    gen_text=text,  # Changed: text → gen_text
    ref_file=ref_audio_path,  # Changed: ref_audio → ref_file
    ref_text=ref_text,
    target_sample_rate=target_sample_rate,
    nfe_step=nfe_step,
    cfg_strength=cfg_strength,
    sway_sampling_coef=sway_sampling_coef,
    speed=speed,
    fix_duration=fix_duration
)
```

#### Lines 139-141: Return Value Handling Fix
**Before:**
```python
# Direct tuple unpacking assumed
audio, sample_rate = model.sample(...)
```

**After:**
```python
# Handle single return value, extract sample rate dynamically
generated_audio = model.sample(...)
# Dynamic sample rate extraction based on actual audio properties
sample_rate = target_sample_rate  # Use target as fallback
```

## Key API Changes Documented

### Parameter Name Changes
| Old Parameter | New Parameter | Context |
|---------------|---------------|---------|
| `model_type` | `model` | F5TTS constructor |
| `text` | `gen_text` | sample() method |
| `ref_audio` | `ref_file` | sample() method |

### New Parameters Added
- `use_ema=True` - Enable EMA (Exponential Moving Average) model usage for better quality

### Return Value Changes
- **Before**: `model.sample()` returned tuple `(audio, sample_rate)`
- **After**: `model.sample()` returns single audio tensor, sample rate handled separately

## Technical Context
- **CUDA Version**: 12.4.0
- **F5TTS Library**: Latest version with breaking API changes
- **Deployment**: RunPod serverless environment
- **Audio Processing**: 22050 Hz default sample rate with dynamic fallback

## Validation
The fix ensures:
1. ✅ Model initializes without parameter errors
2. ✅ Audio generation works with correct parameter names
3. ✅ Return values handled properly without tuple unpacking errors
4. ✅ Sample rate management works with dynamic detection

## Future Considerations
- Monitor F5TTS library updates for further API changes
- Consider version pinning if API stability is required
- Document any additional parameter changes in future updates
- Test compatibility across different model types (F5-TTS, E2-TTS)

## Related Files
- `/runpod-handler.py` - Main handler with API fixes
- Model files in `/models/` directory remain unchanged
- Docker configuration and requirements may need F5TTS version specification

## Keywords
`F5TTS`, `API compatibility`, `RunPod`, `CUDA`, `model initialization`, `parameter mapping`, `tuple unpacking`, `EMA model`