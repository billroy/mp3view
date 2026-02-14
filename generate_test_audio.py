#!/usr/bin/env python3
"""
Test Audio Generator
Creates sample audio files for testing the transcription system
"""
import os
import sys
import subprocess
from pathlib import Path

def generate_test_audio(recordings_dir='recordings', count=5):
    """
    Generate test audio files using macOS text-to-speech
    """
    recordings_path = Path(recordings_dir)
    recordings_path.mkdir(parents=True, exist_ok=True)
    
    # Sample phrases for test recordings
    test_phrases = [
        "Hello, this is test recording number one. The weather is beautiful today.",
        "This is the second test. I am testing the audio transcription system.",
        "Recording number three. Machine learning and artificial intelligence are fascinating topics.",
        "Test four here. Please transcribe this audio accurately.",
        "Final test recording. Thank you for using this transcription service.",
        "The quick brown fox jumps over the lazy dog.",
        "She sells seashells by the seashore.",
        "How much wood would a woodchuck chuck if a woodchuck could chuck wood?",
        "Peter Piper picked a peck of pickled peppers.",
        "I scream, you scream, we all scream for ice cream."
    ]
    
    print(f"Generating {count} test audio files in {recordings_dir}/")
    print("=" * 60)
    
    for i in range(min(count, len(test_phrases))):
        filename = f"test_{i+1:03d}.mp3"
        filepath = recordings_path / filename
        
        # Skip if file already exists
        if filepath.exists():
            print(f"⏭  Skipping {filename} (already exists)")
            continue
        
        print(f"🎤 Generating {filename}...")
        phrase = test_phrases[i]
        
        try:
            # Generate AIFF using macOS say command
            aiff_path = recordings_path / f"temp_{i}.aiff"
            subprocess.run(
                ['say', '-o', str(aiff_path), phrase],
                check=True,
                capture_output=True
            )
            
            # Convert AIFF to MP3 using ffmpeg
            subprocess.run(
                ['ffmpeg', '-i', str(aiff_path), '-y', str(filepath)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Clean up temporary AIFF
            aiff_path.unlink()
            
            print(f"   ✓ Created: {phrase[:50]}...")
            
        except subprocess.CalledProcessError as e:
            print(f"   ✗ Error: {e}")
            continue
        except FileNotFoundError as e:
            print(f"   ✗ Command not found: {e}")
            print("\n   Required tools:")
            print("   - macOS 'say' command (built-in)")
            print("   - ffmpeg (install with: brew install ffmpeg)")
            sys.exit(1)
    
    print("=" * 60)
    print(f"✅ Generated {count} test files")
    print(f"\nTo start the server, run:")
    print(f"  python app.py --recordings-dir {recordings_dir}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate test audio files')
    parser.add_argument(
        '--count',
        type=int,
        default=5,
        help='Number of test files to generate (default: 5, max: 10)'
    )
    parser.add_argument(
        '--recordings-dir',
        type=str,
        default='recordings',
        help='Directory to create test files in (default: recordings)'
    )
    
    args = parser.parse_args()
    
    # Check for required commands
    try:
        subprocess.run(['which', 'say'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("Error: This script requires macOS (uses the 'say' command)")
        sys.exit(1)
    
    try:
        subprocess.run(['which', 'ffmpeg'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("Error: ffmpeg not found")
        print("Install it with: brew install ffmpeg")
        sys.exit(1)
    
    generate_test_audio(args.recordings_dir, args.count)

if __name__ == '__main__':
    main()
