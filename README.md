# F5-TTS RunPod Serverless

This repository contains the implementation of a RunPod serverless worker for the F5-TTS text-to-speech model.

## API Usage

To use this serverless worker, send a POST request to the RunPod endpoint with the following JSON payload:

```json
{
  "input": {
    "text": "Hello, world! This is a test.",
    "speed": 1.0,
    "return_word_timings": true
  }
}
```

### Parameters

- `text` (required): The text to be converted to speech.
- `speed` (optional, default: `1.0`): The speed of the speech.
- `return_word_timings` (optional, default: `true`): Whether to return word-level timings.

### Response

The response will be a JSON object containing the base64-encoded audio data, word timings, and the duration of the audio.

```json
{
  "audio_data": "<base64_encoded_wav_data>",
  "word_timings": [
    {
      "word": "Hello,",
      "start_time": 0.0,
      "end_time": 0.4
    },
    {
      "word": "world!",
      "start_time": 0.45,
      "end_time": 0.8
    },
    ...
  ],
  "duration": 2.5
}
```

## Docker Image

The Docker image for this worker is available on Docker Hub at `gemneye/f5-tts-runpod-serverless`.
