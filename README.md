# F5-TTS RunPod Serverless

This repository contains the implementation of a RunPod serverless worker for the F5-TTS text-to-speech model.

## Features

- **Asynchronous Job Processing:** TTS jobs are processed asynchronously, allowing you to submit a job and check its status later.
- **S3 Integration:** Voice models and output files are stored in an S3 bucket.
- **Custom Voice Models:** You can upload and use your own voice models.

## API Usage

See the [API Reference](API.md) for detailed information about the endpoints.

## Docker Image

The Docker image for this worker is available on Docker Hub at `gemneye/f5-tts-runpod-serverless`.
