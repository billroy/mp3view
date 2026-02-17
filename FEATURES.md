# Feature Improvement Suggestions

## High Value / Low Effort

**1. Keyboard Shortcuts**
Full keyboard navigation: `Space` to play/pause, `J`/`L` to skip ±10s, `↑`/`↓` to navigate list items, `/` to focus the filter box, `R` to re-transcribe selected item.

**2. Transcription Text Editing**
Click to edit a transcription inline. Saves the `.txt` file via a new endpoint. Useful for correcting Whisper errors.

**3. Copy Transcription Button**
Small clipboard icon on each row that copies the transcription text to clipboard. Simple but heavily used.

**4. Sort Controls**
Currently implicit/lexical. Add a sort dropdown: by filename, by date (newest first), by duration, by quality score (`avg_logprob`). Persist choice in `localStorage`.

**5. Playback Speed Control**
`0.5×`, `0.75×`, `1×`, `1.25×`, `1.5×`, `2×` speed buttons in the audio player. HTML5 `audio.playbackRate` — trivial to add.

**6. Whisper Model Switcher**
UI dropdown in toolbar to switch Whisper models (`tiny` → `large`) at runtime without restarting the server. Emit a `set_model` command over SocketIO.

---

## Medium Value / Medium Effort

**7. Bulk Operations**
Checkbox multi-select with a floating action bar: "Re-transcribe selected", "Export selected transcriptions as `.txt`/`.csv`".

**8. Waveform Visualization**
Use the Web Audio API to draw a static waveform image when a file is first loaded/played. Shows at-a-glance where speech vs. silence is.

**9. Export / Download**
- Download audio file directly from the UI
- Download all transcriptions as a single merged `.txt` or `.csv`
- Copy all visible (filtered) transcriptions to clipboard

**10. Transcription Confidence Coloring**
Color-code transcription text based on `avg_logprob` — green for high confidence, yellow for medium, red for low. Helps identify files that need manual review.

---

## High Value / Higher Effort

**11. Speaker Diarization**
Use `pyannote.audio` or `whisperx` to segment who spoke when. Display `[Speaker A]`, `[Speaker B]` labels inline in the transcription text.

**12. Timestamps in Transcriptions**
Whisper already returns segment-level timestamps. Show them in the transcription view and make them clickable to seek the audio player to that position.

**13. Full-Text Search with Highlighting**
Replace the current regex filter with a proper search that highlights matching words within transcription text (not just filters rows). Works well with the existing regex input.

**14. Folder/Group View**
The recordings directory appears to have 963 subdirectories. Add a collapsible folder tree in a sidebar so you can browse by subfolder instead of one flat list.

**15. Batch Import**
Drag-and-drop a folder of audio files onto the UI to upload and transcribe them all. Extend the current upload endpoint to accept any audio format (wav, m4a, ogg) and convert via FFmpeg.

---

## Quality of Life

**16. Persist Filter & Scroll Position**
Save the filter string and scroll position to `sessionStorage` so they survive a page refresh.

**17. Audio Player: Keyboard Seek Bar**
When the seek bar is focused, allow arrow key scrubbing. Currently it's only click/drag.

**18. "Jump to Playing" Button**
When the playing file scrolls off screen, show a floating badge that scrolls back to it on click.

**19. Dark/Light Theme Toggle**
The dark theme is fixed. A simple CSS variable swap for a light mode would help in bright environments.

**20. Health / Stats Panel**
A collapsible panel showing: Whisper model loaded, queue depth, total audio hours transcribed, disk usage of the recordings directory.
