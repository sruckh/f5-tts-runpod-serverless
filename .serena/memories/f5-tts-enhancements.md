The F5-TTS RunPod serverless worker has been enhanced with the following features:
- S3 integration for storing and retrieving voice models and output files.
- Asynchronous job tracking with status updates (QUEUED, PROCESSING, COMPLETED, ERROR).
- New API endpoints for uploading voice models, checking job status, and retrieving results.
- The `local_voice` parameter now accepts both a URL and a local filename.