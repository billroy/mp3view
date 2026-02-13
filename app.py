#!/usr/bin/env python3
"""
Audio Transcription Server
Flask + SocketIO server for managing and transcribing audio recordings
"""
import os
import sys
import argparse
import logging
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import whisper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
RECORDINGS_DIR = Path('recordings')
transcription_queue = queue.Queue()
file_registry: Dict[str, dict] = {}
shutdown_event = threading.Event()
whisper_model = None


class AudioFileHandler(FileSystemEventHandler):
    """Watches for new .mp3 files and queues them for transcription"""

    def on_created(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith('.mp3'):
            logger.info(f"New audio file detected: {event.src_path}")
            file_path = Path(event.src_path)
            self._queue_for_transcription(file_path)

    def on_moved(self, event):
        """Handle file renames/moves into the directory (e.g. macOS atomic writes)"""
        if event.is_directory:
            return

        if event.dest_path.endswith('.mp3'):
            logger.info(f"Audio file moved/renamed into directory: {event.dest_path}")
            file_path = Path(event.dest_path)
            self._queue_for_transcription(file_path)

    def on_deleted(self, event):
        """Handle deletion of .txt transcription files — re-transcribe the associated .mp3"""
        if event.is_directory:
            return

        if event.src_path.endswith('.txt'):
            txt_path = Path(event.src_path)
            mp3_path = txt_path.with_suffix('.mp3')
            filename = mp3_path.name
            if mp3_path.exists() and filename in file_registry:
                logger.info(f"Transcription file deleted externally: {txt_path.name} — re-queuing '{filename}'")
                file_registry[filename]['transcription'] = None
                file_registry[filename]['status'] = 'queued'
                socketio.emit('file_update', file_registry[filename])
                transcription_queue.put(mp3_path)

    def _queue_for_transcription(self, file_path: Path):
        """Add file to transcription queue"""
        transcription_queue.put(file_path)

        # Add to registry immediately
        filename = file_path.name
        if filename not in file_registry:
            size_kb = round(file_path.stat().st_size / 1024) if file_path.exists() else 0
            file_registry[filename] = {
                'filename': filename,
                'size_kb': size_kb,
                'transcription': None,
                'status': 'queued',
                'added': datetime.now().isoformat()
            }
            # Notify clients of new file
            socketio.emit('file_update', file_registry[filename])


def scan_existing_files():
    """Scan recordings directory for existing files"""
    logger.info(f"Scanning {RECORDINGS_DIR} for existing files...")
    
    if not RECORDINGS_DIR.exists():
        logger.warning(f"Recordings directory {RECORDINGS_DIR} does not exist. Creating it...")
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        return
    
    mp3_files = list(RECORDINGS_DIR.glob('*.mp3'))
    logger.info(f"Found {len(mp3_files)} MP3 files")
    
    for mp3_file in mp3_files:
        filename = mp3_file.name
        txt_file = mp3_file.with_suffix('.txt')
        
        # Read existing transcription if available
        transcription = None
        status = 'pending'
        if txt_file.exists():
            try:
                transcription = txt_file.read_text(encoding='utf-8')
                status = 'completed'
            except Exception as e:
                logger.error(f"Error reading transcription for {filename}: {e}")
        
        file_registry[filename] = {
            'filename': filename,
            'size_kb': round(mp3_file.stat().st_size / 1024),
            'transcription': transcription,
            'status': status,
            'added': datetime.fromtimestamp(mp3_file.stat().st_mtime).isoformat()
        }
        
        # Queue files without transcription
        if transcription is None:
            transcription_queue.put(mp3_file)


def load_whisper_model():
    """Load the Whisper model (lazy, once)"""
    global whisper_model
    if whisper_model is None:
        logger.info("[Whisper] Loading 'base' model (first load may download ~140MB)...")
        whisper_model = whisper.load_model("base")
        logger.info("[Whisper] Model loaded successfully")
    return whisper_model


def transcribe_audio(file_path: Path) -> dict:
    """Transcribe an audio file using local OpenAI Whisper.
    Returns dict with 'text', 'avg_logprob', 'no_speech_prob', 'language'."""
    try:
        logger.info(f"Starting transcription of {file_path.name}")
        model = load_whisper_model()
        result = model.transcribe(str(file_path))
        text = result["text"].strip()

        # Compute quality metrics averaged across segments
        segments = result.get("segments", [])
        if segments:
            avg_logprob = sum(s["avg_logprob"] for s in segments) / len(segments)
            no_speech_prob = sum(s["no_speech_prob"] for s in segments) / len(segments)
        else:
            avg_logprob = 0.0
            no_speech_prob = 0.0

        language = result.get("language", "")
        logger.info(f"Transcribed {file_path.name}: lang={language} avg_logprob={avg_logprob:.3f} no_speech={no_speech_prob:.3f}")

        if not text:
            logger.warning(f"Whisper returned empty text for {file_path.name}")
            text = "[Audio not intelligible]"

        return {
            'text': text,
            'avg_logprob': round(avg_logprob, 3),
            'no_speech_prob': round(no_speech_prob, 3),
            'language': language,
        }
    except Exception as e:
        logger.error(f"Error transcribing {file_path.name}: {e}")
        return {
            'text': f"[Transcription error: {str(e)}]",
            'avg_logprob': 0.0,
            'no_speech_prob': 0.0,
            'language': '',
        }


def transcription_worker():
    """Background worker that processes transcription queue"""
    logger.info("Transcription worker started, waiting for items...")

    while not shutdown_event.is_set():
        try:
            # Get file from queue with timeout
            file_path = transcription_queue.get(timeout=1)

            filename = file_path.name
            logger.info(f"[Worker] Dequeued '{filename}' for transcription (queue size now: {transcription_queue.qsize()})")

            # Update status to processing
            if filename in file_registry:
                file_registry[filename]['status'] = 'processing'
                logger.info(f"[Worker] Emitting status 'processing' for '{filename}'")
                socketio.emit('file_update', file_registry[filename])

            # Perform transcription
            logger.info(f"[Worker] Starting transcribe_audio() for '{filename}'...")
            result = transcribe_audio(file_path)
            transcription = result['text']
            logger.info(f"[Worker] transcribe_audio() returned for '{filename}': {len(transcription)} chars")

            # Save transcription to file
            txt_path = file_path.with_suffix('.txt')
            txt_path.write_text(transcription, encoding='utf-8')
            logger.info(f"[Worker] Saved transcription to '{txt_path}'")

            # Update registry
            if filename in file_registry:
                file_registry[filename]['transcription'] = transcription
                file_registry[filename]['avg_logprob'] = result['avg_logprob']
                file_registry[filename]['no_speech_prob'] = result['no_speech_prob']
                file_registry[filename]['language'] = result['language']
                file_registry[filename]['status'] = 'completed'

                # Broadcast update to all clients
                logger.info(f"[Worker] Emitting status 'completed' for '{filename}'")
                socketio.emit('file_update', file_registry[filename])
                logger.info(f"[Worker] Transcription complete and broadcasted for '{filename}'")

            transcription_queue.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"[Worker] Error processing transcription: {e}", exc_info=True)

    logger.info("Transcription worker stopped")


# SocketIO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    import flask
    logger.info(f"Client connected: {flask.request.sid}")
    emit('connected', {'message': 'Connected to transcription server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    import flask
    logger.info(f"Client disconnected: {flask.request.sid}")


@socketio.on('get_files')
def handle_get_files(data=None):
    """Send list of all files to requesting client"""
    import flask
    logger.info(f"Client {flask.request.sid} requested file list")
    
    # Convert registry to list sorted by filename
    files = sorted(file_registry.values(), key=lambda x: x['filename'])
    
    emit('files_list', {
        'files': files,
        'total': len(files)
    })


@socketio.on('request_audio_stream')
def handle_audio_stream_request(data):
    """Handle request to stream audio file"""
    import flask
    filename = data.get('filename')
    
    if not filename:
        emit('error', {'message': 'No filename provided'})
        return
    
    if filename not in file_registry:
        emit('error', {'message': f'File not found: {filename}'})
        return
    
    logger.info(f"Client {flask.request.sid} requesting audio stream for {filename}")
    
    # Send audio URL (will be served via Flask static route)
    emit('audio_stream_ready', {
        'filename': filename,
        'url': f'/audio/{filename}'
    })


@socketio.on('retranscribe')
def handle_retranscribe(data):
    """Delete existing transcription and re-queue the file"""
    import flask
    filename = data.get('filename')

    if not filename:
        emit('error', {'message': 'No filename provided'})
        return

    if filename not in file_registry:
        emit('error', {'message': f'File not found: {filename}'})
        return

    mp3_path = RECORDINGS_DIR / filename
    if not mp3_path.exists():
        emit('error', {'message': f'MP3 file not found on disk: {filename}'})
        return

    logger.info(f"[Retranscribe] Client {flask.request.sid} requested re-transcription of '{filename}'")

    # Delete existing .txt if present
    txt_path = mp3_path.with_suffix('.txt')
    if txt_path.exists():
        txt_path.unlink()
        logger.info(f"[Retranscribe] Deleted '{txt_path.name}'")

    # Update registry and notify all clients
    file_registry[filename]['transcription'] = None
    file_registry[filename]['status'] = 'queued'
    socketio.emit('file_update', file_registry[filename])

    # Queue for transcription
    transcription_queue.put(mp3_path)
    logger.info(f"[Retranscribe] Queued '{filename}' for re-transcription")


# Flask routes
@app.route('/')
def index():
    """Serve the main application"""
    logger.info(f"Serving index.html from {app.static_folder}")
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """Serve audio files"""
    return send_from_directory(RECORDINGS_DIR, filename)


def start_file_watcher():
    """Start the file system watcher"""
    event_handler = AudioFileHandler()
    observer = Observer()
    observer.schedule(event_handler, str(RECORDINGS_DIR), recursive=False)
    observer.start()
    logger.info(f"File watcher started on {RECORDINGS_DIR}")
    return observer


def main():
    """Main entry point"""
    global RECORDINGS_DIR
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Audio Transcription Server')
    parser.add_argument(
        '--recordings-dir',
        type=str,
        default='recordings',
        help='Directory containing audio recordings (default: recordings)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0 - all interfaces)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    
    args = parser.parse_args()
    
    # Set recordings directory
    RECORDINGS_DIR = Path(args.recordings_dir)
    logger.info(f"Using recordings directory: {RECORDINGS_DIR}")
    
    # Verify static folder exists
    static_path = Path(app.static_folder)
    if not static_path.is_absolute():
        static_path = Path(__file__).parent / app.static_folder
    logger.info(f"Static folder path: {static_path}")
    if not static_path.exists():
        logger.warning(f"Static folder does not exist: {static_path}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Script location: {Path(__file__).parent}")
    else:
        logger.info(f"Static folder contents: {list(static_path.iterdir())}")
    
    # Scan existing files
    scan_existing_files()
    
    # Start transcription worker thread
    worker_thread = threading.Thread(target=transcription_worker, daemon=True)
    worker_thread.start()
    
    # Start file watcher
    observer = start_file_watcher()
    
    try:
        # Start server
        logger.info(f"Starting server on {args.host}:{args.port}")
        if args.host == '0.0.0.0':
            logger.info(f"Server accessible at:")
            logger.info(f"  - Local: http://127.0.0.1:{args.port}")
            logger.info(f"  - Network: http://<your-ip-address>:{args.port}")
            logger.info(f"  Find your IP with: ifconfig | grep 'inet ' | grep -v 127.0.0.1")
        else:
            logger.info(f"Open http://{args.host}:{args.port} in your browser")
        socketio.run(
            app,
            host=args.host,
            port=args.port,
            debug=args.debug,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        shutdown_event.set()
        observer.stop()
        observer.join()
        worker_thread.join(timeout=5)
        logger.info("Shutdown complete")


if __name__ == '__main__':
    main()
