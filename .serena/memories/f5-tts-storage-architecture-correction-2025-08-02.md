# F5-TTS Storage Architecture and Model Loading Correction

**Date**: 2025-08-02

## Summary
This session corrected a fundamental misunderstanding of the F5-TTS project's storage architecture. The Dockerfile and runpod-handler.py were modified to correctly load AI models from the persistent `/runpod-volume` at runtime, rather than attempting to load them into the container image during the build process.

## Technical Details

### Problem
- The previous implementation was based on the incorrect assumption that AI models could be loaded into the container image during the build process.
- This led to a `Dockerfile.runpod` that was attempting to pre-load models, which is not feasible due to the large size of the models and the limited storage space in the container.
- The `runpod-handler.py` was not configured to load models from the persistent `/runpod-volume` at runtime.
- A build error, `"/s3_utils-new.py": not found`, was masking these deeper architectural issues.

### Solution
- **Dockerfile Correction**:
    - The entire "BUILD-TIME OPTIMIZATION: Pre-load F5-TTS Models" section was removed from `Dockerfile.runpod`.
    - The associated `HEALTHCHECK` was also removed.
    - The `COPY` commands were corrected to use the correct filenames (`runpod-handler.py` and `s3_utils.py`) to resolve the build error.
- **Handler Correction**:
    - The outdated, asynchronous `runpod-handler.py` was replaced with the more modern, synchronous architecture from `runpod-handler-new.py`.
    - The `initialize_models` function in the new `runpod-handler.py` was modified to set the Hugging Face cache environment variables to point to `/runpod-volume/models`, ensuring models are loaded from the correct persistent volume at runtime.

### Key Architectural Insight
- AI models for this project **must** be loaded from the `/runpod-volume` at runtime. They cannot be included in the container image.

## Impact
The project is now in a state where it can be correctly built and deployed by the RunPod CI/CD system. The runtime architecture correctly reflects the project's storage constraints, and the original build error has been resolved.
