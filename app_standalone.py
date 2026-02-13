#!/usr/bin/env python3
"""
Audio Transcription Server
Flask + SocketIO server for managing and transcribing audio recordings
STANDALONE VERSION - No static folder required
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

from flask import Flask, send_from_directory, render_template_string
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import speech_recognition as sr
from pydub import AudioSegment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
RECORDINGS_DIR = Path('recordings')
transcription_queue = queue.Queue()
file_registry: Dict[str, dict] = {}
shutdown_event = threading.Event()

# Embedded HTML template
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Audio Transcription Studio</title>
    
    <!-- Vue 3 -->
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    
    <!-- Socket.IO Client -->
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=Spectral:wght@300;400;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --bg-primary: #0a0e14;
            --bg-secondary: #141922;
            --bg-tertiary: #1e2530;
            --accent-primary: #00d9ff;
            --accent-secondary: #ff006e;
            --accent-tertiary: #ffbe0b;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --border: #30363d;
            --success: #3fb950;
            --warning: #d29922;
            --processing: #a371f7;
        }
        
        body {
            font-family: 'IBM Plex Mono', monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(0, 217, 255, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 0, 110, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(255, 190, 11, 0.05) 0%, transparent 50%);
            animation: gradient-shift 20s ease infinite;
            z-index: -1;
        }
        
        @keyframes gradient-shift {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            33% { transform: translate(10%, -10%) rotate(120deg); }
            66% { transform: translate(-10%, 10%) rotate(240deg); }
        }
        
        #app {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
            animation: fadeIn 0.6s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .header {
            margin-bottom: 3rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 2rem;
        }
        
        .header h1 {
            font-family: 'Spectral', serif;
            font-size: 3.5rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
            animation: slideInFromTop 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        @keyframes slideInFromTop {
            from { opacity: 0; transform: translateY(-30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .header .subtitle {
            font-size: 0.9rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.15em;
            animation: slideInFromTop 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.1s backwards;
        }
        
        .stats {
            display: flex;
            gap: 2rem;
            margin-top: 1.5rem;
            animation: slideInFromTop 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.2s backwards;
        }
        
        .stat {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 600;
            color: var(--accent-primary);
        }
        
        .stat-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        
        .connection-status {
            position: fixed;
            top: 2rem;
            right: 2rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.25rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 2rem;
            font-size: 0.85rem;
            z-index: 1000;
            animation: slideInFromRight 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        @keyframes slideInFromRight {
            from { opacity: 0; transform: translateX(50px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
            animation: pulse 2s ease infinite;
        }
        
        .status-indicator.disconnected {
            background: var(--text-muted);
            animation: none;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }
        
        .audio-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .audio-item {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            cursor: pointer;
            position: relative;
            overflow: hidden;
            animation: slideInFromBottom 0.5s cubic-bezier(0.16, 1, 0.3, 1) backwards;
        }
        
        @keyframes slideInFromBottom {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .audio-item::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--accent-primary);
            transform: scaleY(0);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        .audio-item:hover {
            background: var(--bg-tertiary);
            border-color: var(--accent-primary);
            transform: translateX(8px);
        }
        
        .audio-item:hover::before {
            transform: scaleY(1);
        }
        
        .audio-item.active {
            border-color: var(--accent-primary);
            background: var(--bg-tertiary);
        }
        
        .audio-item.active::before {
            transform: scaleY(1);
        }
        
        .audio-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
            gap: 1rem;
        }
        
        .audio-title {
            font-family: 'Spectral', serif;
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
            word-break: break-word;
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.85rem;
            border-radius: 1rem;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            white-space: nowrap;
        }
        
        .status-badge.completed {
            background: rgba(63, 185, 80, 0.15);
            color: var(--success);
            border: 1px solid rgba(63, 185, 80, 0.3);
        }
        
        .status-badge.processing {
            background: rgba(163, 113, 247, 0.15);
            color: var(--processing);
            border: 1px solid rgba(163, 113, 247, 0.3);
            animation: processingPulse 2s ease infinite;
        }
        
        @keyframes processingPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        
        .status-badge.pending {
            background: rgba(210, 153, 34, 0.15);
            color: var(--warning);
            border: 1px solid rgba(210, 153, 34, 0.3);
        }
        
        .status-badge.queued {
            background: rgba(139, 148, 158, 0.15);
            color: var(--text-secondary);
            border: 1px solid rgba(139, 148, 158, 0.3);
        }
        
        .transcription {
            color: var(--text-secondary);
            font-size: 0.9rem;
            line-height: 1.7;
            margin-bottom: 1rem;
            font-family: 'Spectral', serif;
        }
        
        .transcription.empty {
            color: var(--text-muted);
            font-style: italic;
        }
        
        .play-button {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 2rem;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .play-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 217, 255, 0.3);
        }
        
        .play-button:active {
            transform: translateY(0);
        }
        
        .play-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .audio-player {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(to top, var(--bg-primary), var(--bg-secondary));
            border-top: 1px solid var(--border);
            padding: 1.5rem 2rem;
            z-index: 999;
            animation: slideInFromBottom 0.5s cubic-bezier(0.16, 1, 0.3, 1);
            backdrop-filter: blur(20px);
        }
        
        .player-container {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .player-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .now-playing {
            font-family: 'Spectral', serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .close-player {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 0.5rem 1rem;
            border-radius: 1.5rem;
            cursor: pointer;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.85rem;
            transition: all 0.2s ease;
        }
        
        .close-player:hover {
            border-color: var(--accent-secondary);
            color: var(--accent-secondary);
        }
        
        .player-controls {
            display: flex;
            gap: 1.5rem;
            align-items: center;
        }
        
        .control-button {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            width: 48px;
            height: 48px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
        }
        
        .control-button:hover {
            background: var(--accent-primary);
            border-color: var(--accent-primary);
            transform: scale(1.1);
        }
        
        .control-button.play-pause {
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border: none;
        }
        
        .control-button.play-pause:hover {
            transform: scale(1.15);
            box-shadow: 0 8px 24px rgba(0, 217, 255, 0.3);
        }
        
        .progress-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .time-display {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: var(--text-muted);
        }
        
        .progress-bar {
            width: 100%;
            height: 6px;
            background: var(--bg-tertiary);
            border-radius: 3px;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
            border-radius: 3px;
            transition: width 0.1s linear;
            position: relative;
        }
        
        .progress-fill::after {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 12px;
            height: 12px;
            background: white;
            border-radius: 50%;
            transform: translate(50%, -25%);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }
        
        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-muted);
        }
        
        .empty-state h3 {
            font-family: 'Spectral', serif;
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: var(--text-secondary);
        }
        
        .spinner {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid var(--text-muted);
            border-top-color: var(--accent-primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2.5rem;
            }
            
            .stats {
                flex-direction: column;
                gap: 1rem;
            }
            
            .connection-status {
                top: 1rem;
                right: 1rem;
            }
            
            .audio-player {
                padding: 1rem;
            }
            
            .player-controls {
                flex-direction: column;
                gap: 1rem;
            }
        }
    </style>
</head>
<body>
    <div id="app">
        <div class="connection-status">
            <div class="status-indicator" :class="{ disconnected: !connected }"></div>
            <span>{{ connected ? 'Connected' : 'Disconnected' }}</span>
        </div>
        
        <header class="header">
            <h1>Audio Transcription Studio</h1>
            <p class="subtitle">Real-time voice-to-text processing</p>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{{ totalFiles }}</div>
                    <div class="stat-label">Total Recordings</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ completedFiles }}</div>
                    <div class="stat-label">Transcribed</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ processingFiles }}</div>
                    <div class="stat-label">Processing</div>
                </div>
            </div>
        </header>
        
        <div class="audio-list" v-if="files.length > 0">
            <div 
                v-for="(file, index) in files" 
                :key="file.filename"
                :style="{ animationDelay: `${index * 0.05}s` }"
                class="audio-item"
                :class="{ active: currentFile && currentFile.filename === file.filename }"
            >
                <div class="audio-header">
                    <h3 class="audio-title">{{ file.filename }}</h3>
                    <span class="status-badge" :class="file.status">
                        <span v-if="file.status === 'processing'" class="spinner"></span>
                        {{ file.status }}
                    </span>
                </div>
                
                <p class="transcription" :class="{ empty: !file.transcription }">
                    {{ file.transcription || 'Awaiting transcription...' }}
                </p>
                
                <button 
                    class="play-button" 
                    @click="playAudio(file)"
                    :disabled="!file.transcription && file.status !== 'completed'"
                >
                    <span>{{ currentFile && currentFile.filename === file.filename && isPlaying ? '⏸' : '▶' }}</span>
                    {{ currentFile && currentFile.filename === file.filename && isPlaying ? 'Pause' : 'Play' }}
                </button>
            </div>
        </div>
        
        <div class="empty-state" v-else>
            <h3>No recordings found</h3>
            <p>Add .mp3 files to the recordings directory to get started</p>
        </div>
        
        <div class="audio-player" v-if="currentFile">
            <div class="player-container">
                <div class="player-header">
                    <div class="now-playing">{{ currentFile.filename }}</div>
                    <button class="close-player" @click="closePlayer">✕ Close</button>
                </div>
                
                <div class="player-controls">
                    <button class="control-button" @click="skipBackward" title="Skip backward 10s">
                        ⏪
                    </button>
                    
                    <button class="control-button play-pause" @click="togglePlayPause">
                        {{ isPlaying ? '⏸' : '▶' }}
                    </button>
                    
                    <button class="control-button" @click="skipForward" title="Skip forward 10s">
                        ⏩
                    </button>
                    
                    <div class="progress-container">
                        <div class="time-display">
                            <span>{{ formatTime(currentTime) }}</span>
                            <span>{{ formatTime(duration) }}</span>
                        </div>
                        <div class="progress-bar" @click="seekTo" ref="progressBar">
                            <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <audio 
                ref="audioElement"
                @timeupdate="updateProgress"
                @loadedmetadata="onAudioLoaded"
                @ended="onAudioEnded"
                @play="isPlaying = true"
                @pause="isPlaying = false"
            ></audio>
        </div>
    </div>
    
    <script>
        const { createApp } = Vue;
        
        createApp({
            data() {
                return {
                    socket: null,
                    connected: false,
                    files: [],
                    currentFile: null,
                    isPlaying: false,
                    currentTime: 0,
                    duration: 0
                }
            },
            
            computed: {
                totalFiles() {
                    return this.files.length;
                },
                
                completedFiles() {
                    return this.files.filter(f => f.status === 'completed').length;
                },
                
                processingFiles() {
                    return this.files.filter(f => f.status === 'processing').length;
                },
                
                progressPercent() {
                    if (this.duration === 0) return 0;
                    return (this.currentTime / this.duration) * 100;
                }
            },
            
            mounted() {
                this.initSocket();
            },
            
            methods: {
                initSocket() {
                    this.socket = io();
                    
                    this.socket.on('connect', () => {
                        console.log('Connected to server');
                        this.connected = true;
                        this.socket.emit('get_files');
                    });
                    
                    this.socket.on('disconnect', () => {
                        console.log('Disconnected from server');
                        this.connected = false;
                    });
                    
                    this.socket.on('files_list', (data) => {
                        console.log('Received files list:', data);
                        this.files = data.files;
                    });
                    
                    this.socket.on('file_update', (fileData) => {
                        console.log('File update received:', fileData);
                        const index = this.files.findIndex(f => f.filename === fileData.filename);
                        
                        if (index >= 0) {
                            this.files[index] = fileData;
                        } else {
                            this.files.push(fileData);
                            this.files.sort((a, b) => a.filename.localeCompare(b.filename));
                        }
                        
                        if (this.currentFile && this.currentFile.filename === fileData.filename) {
                            this.currentFile = fileData;
                        }
                    });
                    
                    this.socket.on('audio_stream_ready', (data) => {
                        console.log('Audio stream ready:', data);
                        this.loadAudio(data.url);
                    });
                    
                    this.socket.on('error', (error) => {
                        console.error('Socket error:', error);
                    });
                },
                
                playAudio(file) {
                    if (this.currentFile && this.currentFile.filename === file.filename) {
                        this.togglePlayPause();
                    } else {
                        this.currentFile = file;
                        this.socket.emit('request_audio_stream', { filename: file.filename });
                    }
                },
                
                loadAudio(url) {
                    const audio = this.$refs.audioElement;
                    audio.src = url;
                    audio.load();
                    audio.play();
                },
                
                togglePlayPause() {
                    const audio = this.$refs.audioElement;
                    if (audio.paused) {
                        audio.play();
                    } else {
                        audio.pause();
                    }
                },
                
                skipBackward() {
                    const audio = this.$refs.audioElement;
                    audio.currentTime = Math.max(0, audio.currentTime - 10);
                },
                
                skipForward() {
                    const audio = this.$refs.audioElement;
                    audio.currentTime = Math.min(audio.duration, audio.currentTime + 10);
                },
                
                seekTo(event) {
                    const progressBar = this.$refs.progressBar;
                    const rect = progressBar.getBoundingClientRect();
                    const percent = (event.clientX - rect.left) / rect.width;
                    const audio = this.$refs.audioElement;
                    audio.currentTime = percent * audio.duration;
                },
                
                updateProgress() {
                    const audio = this.$refs.audioElement;
                    this.currentTime = audio.currentTime;
                },
                
                onAudioLoaded() {
                    const audio = this.$refs.audioElement;
                    this.duration = audio.duration;
                },
                
                onAudioEnded() {
                    this.isPlaying = false;
                },
                
                closePlayer() {
                    const audio = this.$refs.audioElement;
                    audio.pause();
                    this.currentFile = null;
                    this.currentTime = 0;
                    this.duration = 0;
                },
                
                formatTime(seconds) {
                    if (!seconds || isNaN(seconds)) return '0:00';
                    const mins = Math.floor(seconds / 60);
                    const secs = Math.floor(seconds % 60);
                    return `${mins}:${secs.toString().padStart(2, '0')}`;
                }
            }
        }).mount('#app');
    </script>
</body>
</html>'''


class AudioFileHandler(FileSystemEventHandler):
    """Watches for new .mp3 files and queues them for transcription"""
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        if event.src_path.endswith('.mp3'):
            logger.info(f"New audio file detected: {event.src_path}")
            file_path = Path(event.src_path)
            self._queue_for_transcription(file_path)
    
    def _queue_for_transcription(self, file_path: Path):
        """Add file to transcription queue"""
        transcription_queue.put(file_path)
        
        # Add to registry immediately
        filename = file_path.name
        if filename not in file_registry:
            file_registry[filename] = {
                'filename': filename,
                'transcription': None,
                'status': 'queued',
                'added': datetime.now().isoformat()
            }
            # Notify clients of new file
            socketio.emit('file_update', file_registry[filename], broadcast=True)


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
            'transcription': transcription,
            'status': status,
            'added': datetime.fromtimestamp(mp3_file.stat().st_mtime).isoformat()
        }
        
        # Queue files without transcription
        if transcription is None:
            transcription_queue.put(mp3_file)


def transcribe_audio(file_path: Path) -> Optional[str]:
    """
    Transcribe an audio file using speech recognition
    Converts MP3 to WAV first, then uses Google Speech Recognition
    """
    try:
        logger.info(f"Starting transcription of {file_path.name}")
        
        # Convert MP3 to WAV
        wav_path = file_path.with_suffix('.wav')
        audio = AudioSegment.from_mp3(str(file_path))
        audio.export(str(wav_path), format='wav')
        
        # Initialize recognizer
        recognizer = sr.Recognizer()
        
        # Load audio file
        with sr.AudioFile(str(wav_path)) as source:
            audio_data = recognizer.record(source)
        
        # Perform transcription
        text = recognizer.recognize_google(audio_data)
        
        # Clean up temporary WAV file
        wav_path.unlink()
        
        logger.info(f"Successfully transcribed {file_path.name}")
        return text
        
    except sr.UnknownValueError:
        logger.warning(f"Could not understand audio in {file_path.name}")
        return "[Audio not intelligible]"
    except sr.RequestError as e:
        logger.error(f"Could not request results from speech recognition service: {e}")
        return "[Transcription service error]"
    except Exception as e:
        logger.error(f"Error transcribing {file_path.name}: {e}")
        return f"[Transcription error: {str(e)}]"


def transcription_worker():
    """Background worker that processes transcription queue"""
    logger.info("Transcription worker started")
    
    while not shutdown_event.is_set():
        try:
            # Get file from queue with timeout
            file_path = transcription_queue.get(timeout=1)
            
            filename = file_path.name
            
            # Update status to processing
            if filename in file_registry:
                file_registry[filename]['status'] = 'processing'
                socketio.emit('file_update', file_registry[filename], broadcast=True)
            
            # Perform transcription
            transcription = transcribe_audio(file_path)
            
            # Save transcription to file
            txt_path = file_path.with_suffix('.txt')
            txt_path.write_text(transcription, encoding='utf-8')
            
            # Update registry
            if filename in file_registry:
                file_registry[filename]['transcription'] = transcription
                file_registry[filename]['status'] = 'completed'
                
                # Broadcast update to all clients
                socketio.emit('file_update', file_registry[filename], broadcast=True)
                logger.info(f"Transcription complete and broadcasted for {filename}")
            
            transcription_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Error in transcription worker: {e}")
    
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


# Flask routes
@app.route('/')
def index():
    """Serve the main application"""
    return render_template_string(HTML_TEMPLATE)


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
    logger.info(f"Using recordings directory: {RECORDINGS_DIR.absolute()}")
    
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
