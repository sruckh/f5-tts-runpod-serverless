#!/usr/bin/env python3
"""
Convert transcription files (SRT/CSV) to F5-TTS format.

F5-TTS expects simple text files containing the exact transcription
that matches the spoken audio for better voice cloning quality.
"""

import os
import re
import csv
from pathlib import Path

def parse_srt_to_text(srt_content):
    """Convert SRT content to plain text transcription."""
    # Split by double newlines to get subtitle blocks
    blocks = srt_content.strip().split('\n\n')
    
    text_parts = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            # Skip the sequence number (line 0)
            # Skip the timestamp (line 1) 
            # Take the text content (line 2 and beyond)
            text = ' '.join(lines[2:]).strip()
            if text:
                text_parts.append(text)
    
    return ' '.join(text_parts)

def parse_csv_to_text(csv_content):
    """Convert CSV content to plain text transcription."""
    lines = csv_content.strip().split('\n')
    if not lines:
        return ""
    
    text_parts = []
    # Skip header row if it contains "Start" and "End"
    start_idx = 1 if lines[0].lower().find('start') != -1 else 0
    
    for line in lines[start_idx:]:
        if not line.strip():
            continue
            
        # Parse CSV line
        try:
            reader = csv.reader([line])
            row = next(reader)
            if len(row) >= 3:
                # Get the text segment (3rd column)
                text = row[2].strip()
                # Remove quotes if present
                text = text.strip('"').strip("'").strip()
                if text:
                    text_parts.append(text)
        except csv.Error:
            continue
    
    return ' '.join(text_parts)

def convert_voice_transcriptions():
    """Convert all transcription files in the Voices directory."""
    voices_dir = Path("Voices")
    
    if not voices_dir.exists():
        print("❌ Voices directory not found!")
        return
    
    print("🔄 Converting transcription files to F5-TTS format...")
    
    # Get all audio files
    audio_files = []
    for ext in ['*.wav', '*.mp3']:
        audio_files.extend(voices_dir.glob(ext))
    
    converted_count = 0
    
    for audio_file in audio_files:
        voice_name = audio_file.stem
        txt_file = voices_dir / f"{voice_name}.txt"
        
        # Skip if .txt already exists and is recent
        if txt_file.exists():
            print(f"✅ {txt_file.name} already exists, skipping...")
            continue
        
        # Look for corresponding transcription files
        srt_file = voices_dir / f"{voice_name}.srt"
        csv_file = voices_dir / f"{voice_name}.csv"
        
        transcription_text = ""
        
        # Try SRT first
        if srt_file.exists():
            print(f"📝 Processing {srt_file.name}...")
            try:
                with open(srt_file, 'r', encoding='utf-8') as f:
                    srt_content = f.read()
                transcription_text = parse_srt_to_text(srt_content)
                source_file = srt_file.name
            except Exception as e:
                print(f"⚠️ Error reading {srt_file.name}: {e}")
        
        # Try CSV if SRT failed or doesn't exist
        if not transcription_text and csv_file.exists():
            print(f"📊 Processing {csv_file.name}...")
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    csv_content = f.read()
                transcription_text = parse_csv_to_text(csv_content)
                source_file = csv_file.name
            except Exception as e:
                print(f"⚠️ Error reading {csv_file.name}: {e}")
        
        # Write the transcription text file
        if transcription_text:
            try:
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.write(transcription_text)
                print(f"✅ Created {txt_file.name} from {source_file}")
                print(f"   📏 Length: {len(transcription_text)} characters")
                converted_count += 1
            except Exception as e:
                print(f"❌ Error writing {txt_file.name}: {e}")
        else:
            print(f"⚠️ No transcription found for {audio_file.name}")
    
    print(f"\n🎉 Conversion complete! Created {converted_count} text files.")
    
    # Show summary
    print("\n📋 Summary of voice files:")
    for audio_file in sorted(audio_files):
        voice_name = audio_file.stem
        txt_file = voices_dir / f"{voice_name}.txt"
        if txt_file.exists():
            size = txt_file.stat().st_size
            print(f"  ✅ {audio_file.name} → {txt_file.name} ({size} bytes)")
        else:
            print(f"  ❌ {audio_file.name} → No transcription file")

if __name__ == "__main__":
    convert_voice_transcriptions()