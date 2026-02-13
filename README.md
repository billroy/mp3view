# Audio Transcription Studio

A real-time audio transcription application with a Flask backend and Vue 3 frontend. Automatically transcribes audio recordings using Google Speech Recognition and provides a sleek, modern interface for reviewing and playing back recordings.

## Features

- **Automatic Transcription**: Monitors a directory for new .mp3 files and automatically transcribes them
- **Real-time Updates**: Uses SocketIO for instant updates across all connected clients
- **Audio Playback**: Full-featured audio player with play/pause, seek, and skip controls
- **Modern UI**: Distinctive, production-grade interface with smooth animations and beautiful design
- **File Watching**: Automatically detects new recordings added to the directory
- **Background Processing**: Queued transcription system that processes files without blocking

## Architecture

### Backend (Flask + SocketIO)
- Flask web server with SocketIO for bidirectional communication
- Watchdog for file system monitoring (macOS optimized)
- Background worker thread for transcription processing
- Google Speech Recognition for audio-to-text conversion
- Pydub for audio format conversion

### Frontend (Vue 3)
- No build step - uses Vue 3 via CDN
- SocketIO client for real-time updates
- Custom audio player component
- Responsive, animated interface

### Communication Pattern
The application uses a command-based architecture over SocketIO:

**Client → Server Commands:**
- `get_files`: Request list of all recordings
- `request_audio_stream`: Request to play a specific file

**Server → Client Commands:**
- `files_list`: Response with list of files (to specific client)
- `file_update`: Broadcast notification of new/updated file (to all clients)
- `audio_stream_ready`: Response with audio URL (to specific client)

## Prerequisites

- Python 3.8+
- ffmpeg (required by pydub for audio conversion)
- macOS (for file watching - can be adapted for other platforms)

### Install ffmpeg on macOS

```bash
brew install ffmpeg
```

## Installation

1. Clone or download this repository

2. Create a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Start the server with default settings:

```bash
python app.py
```

This will:
- Create a `recordings` directory if it doesn't exist
- Scan for existing .mp3 files
- Start transcribing files without existing .txt files
- Start the web server on http://0.0.0.0:5000 (accessible on your LAN)

The server is accessible at:
- **Local machine**: http://127.0.0.1:5000 or http://localhost:5000
- **Other devices on your network**: http://YOUR-IP-ADDRESS:5000

To find your IP address on macOS:
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

### Command Line Options

```bash
# Custom recordings directory
python app.py --recordings-dir /path/to/your/recordings

# Different port
python app.py --port 8080

# Localhost only (not accessible from LAN)
python app.py --host 127.0.0.1

# Debug mode
python app.py --debug

# Combine options
python app.py --recordings-dir ./audio --port 3000
```

**Note**: By default, the server binds to `0.0.0.0` (all network interfaces), making it accessible from other devices on your LAN. To restrict to localhost only, use `--host 127.0.0.1`.

### Adding Audio Files

1. Place .mp3 files in the recordings directory
2. The server will automatically detect new files
3. Transcription starts automatically in the background
4. All connected clients receive real-time updates
5. Transcriptions are saved as .txt files alongside the .mp3 files

## File Structure

```
audio-transcription-studio/
├── app.py                 # Flask backend server
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── static/
│   └── index.html        # Vue 3 frontend application
└── recordings/           # Audio files directory (created automatically)
    ├── sample1.mp3
    ├── sample1.txt       # Auto-generated transcription
    ├── sample2.mp3
    └── sample2.txt
```

## How It Works

### Startup Sequence

1. **Server starts** and scans the recordings directory
2. **Existing files** are cataloged:
   - Files with .txt transcriptions are marked as "completed"
   - Files without .txt are queued for transcription
3. **File watcher** begins monitoring for new .mp3 files
4. **Background worker** starts processing the transcription queue
5. **Web server** starts and waits for client connections

### Real-time Updates

1. **Client connects** via SocketIO
2. Client requests file list with `get_files` command
3. Server responds with current state
4. As transcriptions complete:
   - Server broadcasts `file_update` to ALL connected clients
   - All clients update their UI in real-time
5. When new files are added:
   - Server detects the file
   - Queues it for transcription
   - Broadcasts initial state to all clients
   - Updates all clients when transcription completes

### Audio Playback

1. User clicks "Play" button on a recording
2. Client sends `request_audio_stream` command with filename
3. Server responds with audio URL (to that client only)
4. Client loads and plays audio in the player component
5. User can control playback with play/pause, seek slider, and skip buttons

## Transcription Process

1. New .mp3 file detected or queued
2. Status updated to "processing"
3. MP3 converted to WAV format (required by speech recognition)
4. Google Speech Recognition processes the audio
5. Text result saved to .txt file
6. Status updated to "completed"
7. All clients notified of the update
8. Temporary WAV file cleaned up

## Troubleshooting

### "No module named 'flask'"
Install requirements: `pip install -r requirements.txt`

### "ffmpeg not found"
Install ffmpeg: `brew install ffmpeg` (macOS)

### "Could not request results from speech recognition service"
- Check internet connection (Google Speech Recognition requires internet)
- Ensure audio file is clear and contains speech
- Try with a different audio file

### Files not appearing
- Check the recordings directory path
- Ensure files are .mp3 format
- Check server logs for errors

### Client not updating
- Check browser console for SocketIO connection errors
- Ensure server is running
- Try refreshing the browser

## Customization

### Change Transcription Engine

The application uses Google Speech Recognition by default. To use a different engine, modify the `transcribe_audio()` function in `app.py`. SpeechRecognition library supports:
- Sphinx (offline)
- Google Cloud Speech
- Wit.ai
- Microsoft Bing
- Houndify
- IBM Speech to Text

### Adjust UI Styling

Edit `/static/index.html` to customize:
- Color scheme (CSS variables in `:root`)
- Fonts (Google Fonts imports)
- Animations and transitions
- Layout and component structure

### Add File Formats

To support additional audio formats beyond .mp3:
1. Update file detection in `AudioFileHandler.on_created()`
2. Ensure pydub can handle the format (may require additional codecs)

## Performance Notes

- **Large Collections**: The app is designed to handle 15,000+ files efficiently
- **Transcription**: Runs in background thread, doesn't block the server
- **Memory**: File registry stored in memory (consider database for >50k files)
- **Network**: SocketIO broadcasts are efficient for moderate numbers of connected clients

## Security Considerations

For production deployment:
- Change the Flask secret key in `app.py`
- Implement authentication for the web interface
- Restrict CORS origins
- Use HTTPS for SocketIO connections
- Validate file uploads if allowing user uploads
- Rate limit API endpoints

## License

This is a demonstration application. Adapt and use as needed for your projects.

## Support

For issues or questions about this application, please check the inline code comments and error logs for debugging information.
