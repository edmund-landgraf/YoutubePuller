# YouTube & Copyright Disclaimer

This application is provided for **personal and educational use only**.

All copyrights and intellectual property rights for audio and video content accessed through YouTube **belong to the original content creators and rights holders**. Use of this application to download or extract audio is **bound by the same copyright protections** that apply to the original content.

By using this application, you agree to comply with:

- YouTube’s **Terms of Service**
- All applicable **copyright laws** and regulations
- Any licenses or permissions granted by the content owner

Users are solely responsible for ensuring they have the legal right to download, copy, convert, or use any content obtained through this application. The author of this software does **not** condone or encourage copyright infringement and as

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
