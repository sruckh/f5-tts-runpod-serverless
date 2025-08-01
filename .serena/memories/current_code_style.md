# F5-TTS RunPod Code Style & Conventions

## Python Code Style
- **PEP 8 Compliant**: Follow Python standard style guide
- **Type Hints**: Use typing module for function signatures and return types
- **Pydantic Models**: Use Pydantic BaseModel for data validation (e.g., WordTiming, TTSResponse)
- **Descriptive Variable Names**: Clear, meaningful variable names (e.g., `job_id`, `audio_url`, `word_timings`)

## Code Organization
- **Modular Structure**: Separate concerns into distinct functions and modules
- **Error Handling**: Comprehensive try/catch blocks with detailed logging
- **Resource Management**: Proper cleanup of temporary files and resources
- **Configuration**: Environment variables for all configurable parameters

## Logging Conventions
- **Emoji Prefixes**: Use emojis for log categorization:
  - 🔄 Processing/Loading
  - ✅ Success
  - ❌ Error
  - ⚠️ Warning
  - 📥 Download
  - ☁️ S3 Operations
  - 🎵 Audio Processing
  - 🗑️ Cleanup

## Documentation Style
- **Docstrings**: Function-level documentation with parameter descriptions
- **Inline Comments**: Explain complex logic and important decisions
- **README**: Clear API usage examples and deployment instructions