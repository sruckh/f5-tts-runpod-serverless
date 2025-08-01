# F5-TTS Command Line Inference Source Code

## Overview
Complete source code for the F5-TTS command line inference interface (`infer-cli.py`) with advanced batch processing capabilities.

## Key Features
- **Multi-voice support** with voice tagging `[voice_name]` in text
- **Batch processing** with chunk saving capabilities
- **Configurable parameters** via TOML config files and CLI arguments
- **Model flexibility** supporting F5TTS_v1_Base, F5TTS_Base, E2TTS_Base
- **Vocoder options** vocos and bigvgan support
- **Audio processing** with silence removal and RMS normalization

## Architecture Components

### Configuration System
- **Primary config**: TOML file format (default: `basic.toml`)
- **CLI override**: Command line arguments override config file values
- **Voice definitions**: Multi-voice configuration support in config["voices"]

### Model Loading
- **Dynamic model selection**: F5TTS_v1_Base | F5TTS_Base | E2TTS_Base
- **Checkpoint handling**: Automatic HuggingFace download via cached_path
- **Vocoder integration**: vocos (mel-24khz) or bigvgan (v2_24khz_100band_256x)

### Text Processing Pipeline
- **Voice tag parsing**: Regex-based `[voice_name]` extraction
- **Text chunking**: Split generation text by voice tags
- **Unicode handling**: Optional ASCII transliteration for file names
- **File input support**: Generate from text files instead of CLI text

### Audio Generation Workflow
1. **Voice preprocessing**: `preprocess_ref_audio_text()` for reference audio/text
2. **Inference processing**: `infer_process()` with configurable parameters
3. **Segment concatenation**: Combine multiple voice segments
4. **Post-processing**: Silence removal and audio normalization

## Key Parameters

### Model Configuration
- `model`: Model name (F5TTS_v1_Base, F5TTS_Base, E2TTS_Base)
- `ckpt_file`: Model checkpoint path (.pt or .safetensors)
- `vocab_file`: Vocabulary file path (.txt)
- `model_cfg`: Model config file (.yaml)

### Audio Processing
- `target_rms`: Output loudness normalization
- `cross_fade_duration`: Segment blending duration
- `speed`: Generation speed multiplier
- `fix_duration`: Total duration constraint
- `remove_silence`: Long silence removal

### Inference Control
- `nfe_step`: Denoising steps (function evaluations)
- `cfg_strength`: Classifier-free guidance strength
- `sway_sampling_coef`: Sway sampling coefficient

### Output Options
- `output_dir`: Output directory path
- `output_file`: Output filename with timestamp default
- `save_chunk`: Save individual voice segments
- `no_legacy_text`: Disable ASCII transliteration

## Voice System Architecture

### Multi-Voice Configuration
```python
voices = {
    "main": {"ref_audio": ref_audio, "ref_text": ref_text},
    "voice1": {"ref_audio": "path1.wav", "ref_text": "transcript1", "speed": 1.2},
    "voice2": {"ref_audio": "path2.wav", "ref_text": "transcript2", "speed": 0.8}
}
```

### Voice Tag Processing
- **Regex patterns**: `r"(?=\[\w+\])"` for splitting, `r"\[(\w+)\]"` for extraction
- **Fallback logic**: Unknown voices default to "main"
- **Per-voice parameters**: Individual speed control per voice

## File Structure Integration

### Input Files
- **Config file**: TOML format with all parameters
- **Reference audio**: WAV files for voice cloning
- **Generation text**: Direct CLI input or file-based input
- **Model files**: Automatic HuggingFace Hub download

### Output Files
- **Main output**: Single concatenated WAV file
- **Chunk outputs**: Individual segment files (optional)
- **Timestamp naming**: Default format `infer_cli_YYYYMMDD_HHMMSS.wav`

## Error Handling & Compatibility

### Legacy Support
- **Pip package compatibility**: Path resolution for example files
- **Unicode handling**: Optional ASCII transliteration for legacy systems
- **Model compatibility**: Automatic vocoder matching for older models

### Path Resolution
```python
# Example file path patches for pip package users
if "infer/examples/" in ref_audio:
    ref_audio = str(files("f5_tts").joinpath(f"{ref_audio}"))
```

## Performance Optimizations

### Model Loading
- **Cached downloads**: HuggingFace Hub caching via cached_path
- **Device specification**: CUDA/CPU device selection
- **Vocoder locality**: Option for local vocoder loading

### Memory Management
- **Segment processing**: Process text chunks individually
- **Audio concatenation**: Efficient numpy array concatenation
- **File handling**: Direct file writing without memory buffering

## Integration Points

### RunPod Deployment
- **Device handling**: Automatic GPU detection and usage
- **Path compatibility**: Absolute path resolution for containers
- **Configuration flexibility**: Environment-based parameter override

### API Integration
- **Parameter mapping**: Direct CLI parameter to API parameter mapping
- **Voice system**: Multi-voice capability for API endpoints
- **Batch processing**: Chunk-based processing for long texts

## Source Code Structure

### Main Components
1. **Argument parsing**: argparse with comprehensive CLI options
2. **Configuration loading**: TOML config file processing
3. **Model initialization**: Dynamic model and vocoder loading
4. **Text processing**: Voice tag parsing and text chunking
5. **Audio generation**: Inference loop with segment processing
6. **Output handling**: File writing and post-processing

### Key Functions
- `main()`: Primary execution function with voice processing loop
- `preprocess_ref_audio_text()`: Reference audio/text preprocessing
- `infer_process()`: Core TTS inference function
- `load_model()`: Model loading and initialization
- `load_vocoder()`: Vocoder loading (vocos/bigvgan)

## Usage Examples

### Basic Generation
```bash
python3 infer-cli.py -r ref.wav -s "Reference text" -t "Generated text" -o output/
```

### Multi-Voice Generation
```bash
python3 infer-cli.py -t "[voice1]Hello from voice 1. [voice2]And hello from voice 2."
```

### Batch Processing
```bash
python3 infer-cli.py -f input.txt --save_chunk -o output/ --remove_silence
```

This comprehensive CLI interface provides the foundation for F5-TTS text-to-speech generation with advanced features like multi-voice support, batch processing, and flexible configuration options.