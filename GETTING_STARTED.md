# Audio Transcription Studio - Getting Started

## What You Have

A complete Flask/Vue 3 application for automatic audio transcription with real-time updates.

## Quick Start (3 Steps)

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install ffmpeg (macOS)
brew install ffmpeg
```

### 2. Start the Server

```bash
python app.py
```

### 3. Open Browser

Navigate to: **http://127.0.0.1:3000**

## What Happens Next

1. Server scans the `recordings` directory
2. Any .mp3 files without .txt files are queued for transcription
3. Background worker processes transcriptions one by one
4. Web interface updates in real-time as transcriptions complete
5. Click "Play" on any recording to listen with full playback controls

## Project Structure

```
audio-transcription-studio/
├── app.py                      # Main Flask server
├── static/index.html          # Vue 3 frontend
├── requirements.txt           # Python dependencies
├── generate_test_audio.py     # Test file generator
├── README.md                  # Full documentation
├── QUICKSTART.md             # Quick start guide
├── API.md                    # API documentation
├── PROJECT.md                # Project overview
└── .gitignore                # Git ignore rules
```

## Key Features

- **Automatic Transcription**: Drop .mp3 files in the directory, get transcriptions
- **Real-Time Updates**: All connected browsers update simultaneously
- **Beautiful UI**: Modern, production-grade interface
- **Full Audio Player**: Play, pause, seek, skip controls
- **Background Processing**: Non-blocking transcription queue
- **File Watching**: Automatically detects new files

## Testing It Out

Generate test audio files:
```bash
python generate_test_audio.py --count 5
```

This creates 5 sample .mp3 files in the `recordings` directory.

## Command Line Options

```bash
# Custom directory
python app.py --recordings-dir /path/to/audio

# Different port
python app.py --port 8080

# Network accessible
python app.py --host 0.0.0.0

# Debug mode
python app.py --debug
```

## Documentation

- **README.md**: Complete setup and usage guide
- **QUICKSTART.md**: Step-by-step quick start
- **API.md**: SocketIO command reference
- **PROJECT.md**: Architecture and design overview

## Requirements

- Python 3.8+
- ffmpeg (for audio conversion)
- macOS (for file watching - adaptable to other platforms)
- Internet connection not required (Whisper runs locally)

## Architecture

**Backend:**
- Flask + SocketIO for server
- Watchdog for file monitoring
- OpenAI Whisper for local transcription

**Frontend:**
- Vue 3 (no build required)
- SocketIO client
- Native HTML5 audio

**Communication:**
- Two-way command pattern over SocketIO
- Broadcast updates for new/updated files
- Unicast responses for requests

## Next Steps

1. Read QUICKSTART.md for detailed setup
2. Review API.md to understand the protocol
3. Check PROJECT.md for customization options
4. Explore app.py and static/index.html for implementation details

## Support

Check the inline code comments and README.md for troubleshooting tips.

---

**Happy transcribing! 🎤→📝**
