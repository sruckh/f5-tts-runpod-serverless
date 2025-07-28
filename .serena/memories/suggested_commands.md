### F5-TTS Server

**Build and run the server:**
```bash
docker-compose up -d
```

**Test the server:**
```bash
# Test TTS generation
curl -X POST "http://localhost:7860/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Welcome to our amazing story",
    "voice_id": "default",
    "speed": 1.0,
    "return_word_timings": true
  }'

# Test audio alignment
curl -X POST "http://localhost:7860/align" \
  -F "audio=@test_audio.wav" \
  -F "text=Welcome to our amazing story"
```

### Whisper Server

**Build and run the server:**
```bash
# Navigate to the whisper-tts directory first
docker-compose up -d
```

**Test the server:**
```bash
# Test transcription with word timings
curl -X POST "http://localhost:9000/transcribe" \
  -F "audio=@test_audio.wav" \
  -F "return_word_timings=true" \
  -F "language=en"
```

### General Docker Commands

**View logs:**
```bash
docker logs f5-tts-server
docker logs whisper-tts-server
```

**Monitor resource usage:**
```bash
docker stats f5-tts-server whisper-tts-server
```