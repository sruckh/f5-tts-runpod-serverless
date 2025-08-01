# F5-TTS API Enhancement and Dependency Update

## Task Summary
**Task ID**: TASK-2025-08-02-002

This task involved two main changes:
1.  **Updating the `transformers` library**: The `transformers` library was updated to version `>=4.48.1` in the `Dockerfile.runpod`.
2.  **Adding a download endpoint**: A new `/download` endpoint was added to the API to allow users to download the generated audio files.

## Changes Implemented

### 1. `Dockerfile.runpod`
- Added the following line to install the required version of the `transformers` library:
  ```dockerfile
  RUN pip install --upgrade "transformers>=4.48.1"
  ```

### 2. `s3_utils.py`
- Added a new function `download_file_from_s3_to_memory` to download files from S3 as a byte stream:
  ```python
  def download_file_from_s3_to_memory(object_name):
      """Download a file from S3 and return it as a byte stream."""
      if not s3_client or not S3_BUCKET:
          print("S3 not configured properly")
          return None
      try:
          s3_object = s3_client.get_object(Bucket=S3_BUCKET, Key=object_name)
          return s3_object['Body'].read()
      except ClientError as e:
          if e.response['Error']['Code'] == "404":
              print(f"The object {object_name} does not exist.")
          else:
              print(f"An error occurred: {e}")
          return None
  ```

### 3. `runpod-handler.py`
- Added a new `/download` endpoint to the `handler` function:
  ```python
  if endpoint == "download":
      job_id = job_input.get("job_id")
      if not job_id:
          return {"error": "job_id is required for download"}

      output_key = f"output/{job_id}.wav"
      
      try:
          audio_data = download_file_from_s3_to_memory(output_key)
          if audio_data:
              return {
                  "audio_data": base64.b64encode(audio_data).decode('utf-8'),
                  "content_type": "audio/wav"
              }
          else:
              return {"error": f"Audio file not found for job_id: {job_id}"}
      except Exception as e:
          return {"error": f"Failed to download audio file: {str(e)}"}
  ```
- The TTS generation endpoint now returns a `job_id`:
  ```python
  # ... inside the TTS generation endpoint ...
  job_id = str(uuid.uuid4())
  output_key = f"output/{job_id}.wav"
  audio_url = upload_to_s3(output_file, output_key)
  # ...
  return {
      "audio_url": audio_url,
      "duration": duration,
      "text": text,
      "status": "completed",
      "job_id": job_id
  }
  ```
- Imported `download_file_from_s3_to_memory` and `base64`.

## Reason for Changes
- The `transformers` library needed to be updated to a more recent version.
- The S3 URLs for generated audio are not publicly accessible, so a download endpoint was required to provide access to the files.
