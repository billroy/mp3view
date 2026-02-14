# API Documentation

## SocketIO Communication Protocol

The Audio Transcription Studio uses SocketIO for bidirectional, real-time communication between the client and server. All messages use JSON format.

## Connection

### Client Connects
```javascript
// Client connects to server
const socket = io();

socket.on('connect', () => {
    console.log('Connected to server');
});
```

### Server Acknowledgment
```javascript
// Server sends confirmation
{
    event: 'connected',
    data: {
        message: 'Connected to transcription server'
    }
}
```

## Client → Server Commands

### 1. Get Files List

Request the complete list of all audio files and their transcription status.

**Event Name:** `get_files`

**Payload:** `null` or `{}`

**Example:**
```javascript
socket.emit('get_files');
```

**Response Event:** `files_list` (see Server → Client Commands)

---

### 2. Request Audio Stream

Request to play a specific audio file.

**Event Name:** `request_audio_stream`

**Payload:**
```javascript
{
    filename: string  // Name of the .mp3 file to stream
}
```

**Example:**
```javascript
socket.emit('request_audio_stream', {
    filename: 'recording_001.mp3'
});
```

**Response Event:** `audio_stream_ready` (see Server → Client Commands)

**Error Response:** `error` event if file not found

---

## Server → Client Commands

### 1. Files List Response

Sent in response to `get_files` command. Returns to the requesting client only.

**Event Name:** `files_list`

**Payload:**
```javascript
{
    files: [
        {
            filename: string,        // Name of the audio file
            transcription: string | null,  // Transcribed text or null
            status: string,          // 'queued' | 'pending' | 'processing' | 'completed'
            added: string           // ISO timestamp of when file was added
        },
        // ... more files
    ],
    total: number                   // Total number of files
}
```

**Example:**
```javascript
socket.on('files_list', (data) => {
    console.log(`Received ${data.total} files`);
    data.files.forEach(file => {
        console.log(`${file.filename}: ${file.status}`);
    });
});
```

---

### 2. File Update Notification

Broadcast to ALL connected clients when a file is added or its transcription is updated.

**Event Name:** `file_update`

**Payload:**
```javascript
{
    filename: string,              // Name of the audio file
    transcription: string | null,  // Transcribed text (null if not yet complete)
    status: string,                // Current status
    added: string                 // ISO timestamp
}
```

**Status Values:**
- `queued` - File detected, waiting for transcription worker
- `pending` - File exists without transcription
- `processing` - Currently being transcribed
- `completed` - Transcription finished

**Example:**
```javascript
socket.on('file_update', (fileData) => {
    console.log(`Update for ${fileData.filename}: ${fileData.status}`);
    if (fileData.status === 'completed') {
        console.log(`Transcription: ${fileData.transcription}`);
    }
});
```

**Broadcast Behavior:** This event is sent to ALL connected clients simultaneously, enabling real-time synchronization across multiple browser windows.

---

### 3. Audio Stream Ready

Sent in response to `request_audio_stream` command. Returns to the requesting client only.

**Event Name:** `audio_stream_ready`

**Payload:**
```javascript
{
    filename: string,  // Name of the audio file
    url: string       // URL path to stream the audio (relative to server)
}
```

**Example:**
```javascript
socket.on('audio_stream_ready', (data) => {
    const audio = document.querySelector('audio');
    audio.src = data.url;
    audio.play();
});
```

---

### 4. Error

Sent when an error occurs processing a client request.

**Event Name:** `error`

**Payload:**
```javascript
{
    message: string  // Error description
}
```

**Example:**
```javascript
socket.on('error', (error) => {
    console.error('Server error:', error.message);
});
```

---

## HTTP Endpoints

While the main application uses SocketIO, there are also HTTP endpoints:

### 1. Serve Main Application

**URL:** `/`  
**Method:** `GET`  
**Response:** HTML page (Vue 3 application)

### 2. Serve Audio Files

**URL:** `/audio/<filename>`  
**Method:** `GET`  
**Parameters:**
- `filename` - Name of the .mp3 file

**Response:** Audio file stream

**Example:**
```
GET /audio/recording_001.mp3
```

---

## Data Flow Examples

### Example 1: Client Startup

```
1. Client → Server: connect()
2. Server → Client: connected event
3. Client → Server: get_files command
4. Server → Client: files_list response with all files
```

### Example 2: New File Added

```
1. User adds file.mp3 to recordings directory
2. Server detects file via file watcher
3. Server → All Clients: file_update (status: 'queued')
4. Server starts transcription
5. Server → All Clients: file_update (status: 'processing')
6. Transcription completes
7. Server saves transcription to file.txt
8. Server → All Clients: file_update (status: 'completed', transcription: '...')
```

### Example 3: Playing Audio

```
1. Client → Server: request_audio_stream { filename: 'test.mp3' }
2. Server → Client: audio_stream_ready { url: '/audio/test.mp3' }
3. Client loads audio from URL and plays
```

### Example 4: Multi-Client Synchronization

```
Client A and Client B are both connected

1. File added to server
2. Server → Client A: file_update
   Server → Client B: file_update (simultaneously)
3. Both clients update their UI at the same time
```

---

## Implementation Notes

### Client Side (Vue 3)

```javascript
// Initialize SocketIO connection
const socket = io();

// Listen for connection
socket.on('connect', () => {
    // Request initial data
    socket.emit('get_files');
});

// Handle file list
socket.on('files_list', (data) => {
    this.files = data.files;
});

// Handle updates (broadcast from server)
socket.on('file_update', (fileData) => {
    // Update or add file in local state
    const index = this.files.findIndex(f => f.filename === fileData.filename);
    if (index >= 0) {
        this.files[index] = fileData;
    } else {
        this.files.push(fileData);
    }
});
```

### Server Side (Flask)

```python
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

# Handle client command
@socketio.on('get_files')
def handle_get_files():
    emit('files_list', {
        'files': list(file_registry.values()),
        'total': len(file_registry)
    })

# Broadcast update to all clients
def broadcast_file_update(file_data):
    socketio.emit('file_update', file_data, broadcast=True)
```

---

## Error Handling

All commands should be wrapped in try-catch blocks:

```javascript
try {
    socket.emit('get_files');
} catch (error) {
    console.error('Failed to request files:', error);
}

socket.on('error', (error) => {
    console.error('Server error:', error.message);
    // Show user-friendly error message
});
```

---

## Testing the API

### Using Browser Console

```javascript
// Connect to server
const socket = io();

// Request files
socket.emit('get_files');

// Listen for response
socket.on('files_list', (data) => console.log(data));

// Request audio
socket.emit('request_audio_stream', { filename: 'test.mp3' });

// Listen for ready
socket.on('audio_stream_ready', (data) => console.log(data));
```

### Using Python Client

```python
import socketio

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected')
    sio.emit('get_files')

@sio.on('files_list')
def on_files_list(data):
    print(f"Received {len(data['files'])} files")

sio.connect('http://localhost:3000')
sio.wait()
```
