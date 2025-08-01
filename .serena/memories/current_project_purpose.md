# F5-TTS RunPod Serverless Project Purpose

This project implements a **RunPod serverless worker** for the F5-TTS text-to-speech model. Key features:

- **Asynchronous Job Processing**: TTS jobs are processed asynchronously with job status tracking
- **S3 Integration**: Voice models and output files stored in S3-compatible storage (including Backblaze B2)
- **Custom Voice Models**: Upload and use custom voice models with automatic transcription
- **RunPod Serverless**: Optimized for serverless deployment on RunPod GPU infrastructure
- **F5-TTS Integration**: Uses official F5-TTS models with dynamic loading for resource efficiency

The project serves as a Docker-containerized serverless function that can be deployed on RunPod for scalable text-to-speech generation.