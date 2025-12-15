import os
import re
import subprocess
import threading
from queue import Queue

import yt_dlp
import tkinter as tk
from tkinter import scrolledtext, filedialog, Toplevel

# -------------------------------------------------------------------
# DEFAULT CONFIG VALUES
# -------------------------------------------------------------------
FFMPEG_PATH = r"d:\ffmpeg\bin\ffmpeg.exe"
OUTPUT_FOLDER = r"d:\temp\youtubeaudiooutput"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

default_url = "https://www.youtube.com/watch?v=qmlYf5d-Cvo"

# -------------------------------------------------------------------
# GLOBALS
# -------------------------------------------------------------------
log_queue: Queue[str] = Queue()
RUNNING = False  # to prevent double-click spam


# -------------------------------------------------------------------
# LOGGING TO GUI (via queue)
# -------------------------------------------------------------------
def gui_print(msg: str):
    """Thread-safe: push messages into the queue."""
    if msg is None:
        return
    msg = str(msg).rstrip("\n")
    if msg:
        log_queue.put(msg)


def process_log_queue():
    """Called via root.after; pulls messages and writes to console."""
    global RUNNING
    try:
        while not log_queue.empty():
            msg = log_queue.get_nowait()
            if msg == "__DONE__":
                RUNNING = False
                ok_button.config(state="normal")
            else:
                console.configure(state="normal")
                console.insert(tk.END, msg + "\n")
                console.see(tk.END)
                console.configure(state="disabled")
    finally:
        root.after(50, process_log_queue)  # schedule next poll


# -------------------------------------------------------------------
# yt_dlp LOGGER + PROGRESS HOOKS
# -------------------------------------------------------------------
class GuiLogger:
    def debug(self, msg):
        gui_print(msg)

    def info(self, msg):
        gui_print(msg)

    def warning(self, msg):
        gui_print(f"WARNING: {msg}")

    def error(self, msg):
        gui_print(f"ERROR: {msg}")


def ytdlp_progress_hook(d):
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        eta = d.get("eta")
        line = f"[download] {percent} ETA {eta}s {speed}"
        gui_print(line)
    elif d["status"] == "finished":
        filename = d.get("filename", "")
        gui_print(f"[download] Finished downloading: {filename}")
        gui_print("[download] Now post-processing audio...")


# -------------------------------------------------------------------
# UTILITIES
# -------------------------------------------------------------------
def is_local_file(path: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:\\", path))


def run_ffmpeg_streamed(cmd):
    """Run ffmpeg in a worker thread and stream its output to GUI."""
    gui_print("⚙️ Running ffmpeg...")
    try:
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        for line in p.stdout:
            gui_print(line.rstrip("\n"))

        p.wait()
        gui_print("✅ ffmpeg completed.")
    except Exception as e:
        gui_print(f"❌ ffmpeg error: {e}")


# -------------------------------------------------------------------
# CORE OPERATIONS (called from worker thread)
# -------------------------------------------------------------------
def convert_local_mp4_to_mp3(filepath: str):
    global FFMPEG_PATH, OUTPUT_FOLDER

    if not os.path.isfile(filepath):
        gui_print(f"❌ File does not exist: {filepath}")
        return

    if not filepath.lower().endswith(".mp4"):
        gui_print("❌ Only .mp4 files are supported for local conversion.")
        return

    filename = os.path.splitext(os.path.basename(filepath))[0]
    output_mp3 = os.path.join(OUTPUT_FOLDER, f"{filename}.mp3")

    cmd = [
        FFMPEG_PATH,
        "-i",
        filepath,
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ab",
        "192k",
        output_mp3,
    ]

    gui_print(f"🎵 Converting local file → {output_mp3}")
    run_ffmpeg_streamed(cmd)
    gui_print(f"✅ MP3 saved: {output_mp3}")


def download_youtube_audio(url: str):
    global FFMPEG_PATH, OUTPUT_FOLDER

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_FOLDER, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "ffmpeg_location": FFMPEG_PATH,
        "quiet": False,       # allow logs
        "verbose": True,      # more detail
        "logger": GuiLogger(),
        "progress_hooks": [ytdlp_progress_hook],
    }

    gui_print(f"🎧 Downloading from YouTube: {url}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    gui_print(f"✅ Downloaded: {info.get('title', 'unknown')}")
    gui_print(f"📁 Saved to: {OUTPUT_FOLDER}")


# -------------------------------------------------------------------
# WORKER + CALLBACK
# -------------------------------------------------------------------
def worker(url_or_file: str, out_folder: str):
    global OUTPUT_FOLDER
    try:
        if out_folder:
            OUTPUT_FOLDER = out_folder
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)

        if not url_or_file:
            url_or_file = default_url

        if url_or_file.lower().startswith(("http://", "https://")):
            download_youtube_audio(url_or_file)
        elif is_local_file(url_or_file):
            convert_local_mp4_to_mp3(url_or_file)
        else:
            gui_print("❌ Input must be a YouTube URL (http/https) or a local .mp4 file.")
    except Exception as e:
        gui_print(f"❌ Unexpected error: {e}")
    finally:
        # callback signal back to GUI
        log_queue.put("__DONE__")


def run_process():
    global RUNNING
    if RUNNING:
        return  # already running
    RUNNING = True
    ok_button.config(state="disabled")

    url_or_file = input_box.get().strip()
    out_folder = output_box.get().strip()

    t = threading.Thread(target=worker, args=(url_or_file, out_folder), daemon=True)
    t.start()


# -------------------------------------------------------------------
# CONFIG MODAL
# -------------------------------------------------------------------
def open_config_window():
    config_win = Toplevel(root)
    config_win.title("Location of FFmpeg")
    config_win.geometry("500x180")
    config_win.resizable(False, False)

    tk.Label(config_win, text="FFmpeg executable location:").pack(
        anchor="w", padx=10, pady=(10, 0)
    )

    ffmpeg_entry = tk.Entry(config_win, width=60)
    ffmpeg_entry.insert(0, FFMPEG_PATH)
    ffmpeg_entry.pack(padx=10, pady=5)

    def browse_ffmpeg():
        file_path = filedialog.askopenfilename(
            title="Select ffmpeg.exe",
            filetypes=[("FFmpeg Executable", "ffmpeg.exe"), ("All Files", "*.*")],
        )
        if file_path:
            ffmpeg_entry.delete(0, tk.END)
            ffmpeg_entry.insert(0, file_path)

    def save_config():
        global FFMPEG_PATH
        new_path = ffmpeg_entry.get().strip()
        if os.path.isfile(new_path):
            FFMPEG_PATH = new_path
            gui_print(f"⚙️ FFmpeg path updated:\n{FFMPEG_PATH}")
            config_win.destroy()
        else:
            gui_print("❌ Invalid FFmpeg path selected.")

    browse_btn = tk.Button(config_win, text="Browse…", command=browse_ffmpeg)
    browse_btn.pack(pady=5)

    save_btn = tk.Button(config_win, text="Save", width=12, command=save_config)
    save_btn.pack(pady=10)


# -------------------------------------------------------------------
# TKINTER UI
# -------------------------------------------------------------------
root = tk.Tk()
root.title("YouTube / MP4 → MP3 Converter")
root.geometry("780x600")

tk.Label(root, text="YouTube URL or Local MP4 Path:").pack(
    anchor="w", padx=10, pady=(10, 0)
)
input_box = tk.Entry(root, width=100)
input_box.insert(0, default_url)
input_box.pack(padx=10, pady=5)

tk.Label(root, text="Output Folder:").pack(anchor="w", padx=10)
output_box = tk.Entry(root, width=100)
output_box.insert(0, OUTPUT_FOLDER)
output_box.pack(padx=10, pady=5)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

ok_button = tk.Button(button_frame, text="OK", width=20, command=run_process)
ok_button.grid(row=0, column=0, padx=10)

config_button = tk.Button(button_frame, text="Config", width=20, command=open_config_window)
config_button.grid(row=0, column=1, padx=10)

tk.Label(root, text="Status Console:").pack(anchor="w", padx=10)

console = scrolledtext.ScrolledText(
    root, width=100, height=20, bg="black", fg="lime", insertbackground="white"
)
console.configure(font=("Consolas", 10))
console.pack(padx=10, pady=5)
console.configure(state="disabled")

# start log processing "callback loop"
root.after(50, process_log_queue)

root.mainloop()
