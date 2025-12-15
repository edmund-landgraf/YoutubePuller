# YouTube / MP3 / WebM Audio Downloader (GUI)

A cross-platform **Tkinter-based GUI application** for downloading audio from YouTube and converting it to **MP3** or **WebM**, built on top of **yt-dlp** and **FFmpeg**.

Designed for **non-interactive, reliable batch usage**, with real-time console output streamed directly into the UI.

---

## Features

- 🎧 Download audio from **YouTube URLs**
- 🎵 Convert to **MP3 (192 kbps)** or save **WebM**
- 🖥️ GUI interface (Tkinter)
- ⚙️ Configurable FFmpeg path and output folder
- 🪟 Windows mode (custom FFmpeg + output path)
- 🍎 Mac mode (locked config for system FFmpeg)
- 📜 Real-time yt-dlp + FFmpeg logs in UI
- 🧹 Automatic temp file cleanup
- 🔁 Safe handling of existing output files (no hangs)

---

## Supported Inputs

Accepted input types:

- ✅ YouTube URLs  
  - `https://www.youtube.com/watch?v=...`
  - `https://youtu.be/...`
  - `www.youtube.com/watch?v=...` *(auto-corrected)*

- ✅ Local `.mp4` files (audio extraction)

Rejected input types:

- ❌ Non-YouTube URLs  
- ❌ Unsupported file formats  
- ❌ Invalid paths or text

---

## Output Formats

| Format | Behavior |
|-----|-----|
| `.mp3` | Best audio downloaded → converted to MP3 via FFmpeg |
| `.webm` | Best WebM audio saved directly |

> MP3 conversion uses **libmp3lame @ 192 kbps**

---

## File Overwrite Behavior

- **yt-dlp**: Overwrites existing files by default
- **FFmpeg**: Forced overwrite using `-y` (prevents GUI hangs)

This ensures **non-interactive execution** with no blocking prompts.

---

## Requirements

### Python
- Python **3.9+**

### Python packages
```bash
pip install yt-dlp
