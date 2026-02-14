# Quick Start Guide

## Installation Steps

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install ffmpeg (macOS):**
   ```bash
   brew install ffmpeg
   ```

3. **Create test directory structure:**
   ```bash
   mkdir -p recordings
   ```

## Running the Application

### Start the server:
```bash
python app.py
```

You should see output like:
```
INFO - Scanning recordings for existing files...
INFO - Found 0 MP3 files
INFO - Using recordings directory: recordings
INFO - Transcription worker started
INFO - File watcher started on recordings
INFO - Starting server on 0.0.0.0:3000
```

### Access the web interface:
Open your browser to:
- **On the same computer**: http://127.0.0.1:3000 or http://localhost:3000
- **From another device on your network**: http://YOUR-IP-ADDRESS:3000

To find your IP address (macOS):
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

Example: If your IP is `192.168.1.100`, access from any device on your network at `http://192.168.1.100:3000`

## Testing with Sample Audio

### Option 1: Use existing audio files
Copy your .mp3 files to the `recordings` directory:
```bash
cp /path/to/your/audio.mp3 recordings/
```

The server will automatically:
- Detect the new file
- Queue it for transcription
- Update all connected browsers in real-time

### Option 2: Generate text-to-speech audio
Use macOS `say` command to generate test audio:
```bash
say -o recordings/test1.aiff "Hello, this is a test recording for the transcription system."
ffmpeg -i recordings/test1.aiff recordings/test1.mp3
rm recordings/test1.aiff
```

## What to Expect

1. **When you start the server:**
   - Browser shows connection indicator (green dot)
   - Stats show: 0 total, 0 transcribed, 0 processing

2. **When you add a file:**
   - File appears immediately with "queued" status
   - Status changes to "processing" (purple badge)
   - After transcription completes, status becomes "completed" (green badge)
   - Transcription text appears
   - Play button becomes active

3. **When you click Play:**
   - Audio player appears at bottom of screen
   - Shows filename and playback controls
   - Progress bar updates in real-time
   - Can skip forward/backward 10 seconds

## Testing Multi-Client Updates

1. Open the app in multiple browser windows/tabs
2. Add a new audio file to the recordings directory
3. Watch all browser windows update simultaneously
4. Each client receives the same real-time updates

## Command Line Options

```bash
# Use a different directory
python app.py --recordings-dir /Users/you/Music/Recordings

# Localhost only (not accessible from other devices)
python app.py --host 127.0.0.1

# Use a different port
python app.py --port 8080

# Enable debug mode (verbose logging)
python app.py --debug
```

**Default behavior**: Server is accessible on your entire local network (0.0.0.0). Use `--host 127.0.0.1` to restrict to localhost only.

## Troubleshooting Quick Checks

### Server won't start?
- Check if port 3000 is already in use: `lsof -i :3000`
- Try a different port: `python app.py --port 8080`

### Files not transcribing?
- Check internet connection (Google Speech Recognition requires internet)
- Look at server console for error messages
- Ensure audio file contains clear speech
- Try with a simple test file first

### Browser not connecting?
- Check that server is running
- Verify URL is http://127.0.0.1:3000
- Check browser console (F12) for errors
- Try refreshing the page
