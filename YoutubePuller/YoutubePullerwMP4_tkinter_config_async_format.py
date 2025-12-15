import os
import re
import subprocess
import threading
from queue import Queue

import yt_dlp
import tkinter as tk
from tkinter import scrolledtext, filedialog, Toplevel

# ================================================================
#  DEFAULT CONFIG
# ================================================================
FFMPEG_PATH = r"d:\ffmpeg\bin\ffmpeg.exe"
OUTPUT_FOLDER = r"d:\temp\youtubeaudiooutput"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

default_url = "https://www.youtube.com/watch?v=qmlYf5d-Cvo"

log_queue = Queue()
RUNNING = False


# ================================================================
#  GUI LOGGING
# ================================================================
def gui_print(msg: str):
    if msg:
        log_queue.put(str(msg))


def process_log_queue():
    global RUNNING
    while not log_queue.empty():
        msg = log_queue.get_nowait()

        if msg == "__DONE__":
            RUNNING = False
            ok_button.config(state="normal")
            continue

        console.configure(state="normal")
        console.insert(tk.END, msg.rstrip() + "\n")
        console.see(tk.END)
        console.configure(state="disabled")

    root.after(50, process_log_queue)


# ================================================================
#  YT-DLP LOGGER + HOOKS
# ================================================================
class GuiLogger:
    def debug(self, msg):
        gui_print(msg)

    def info(self, msg):
        gui_print(msg)

    def warning(self, msg):
        gui_print("WARNING: " + msg)

    def error(self, msg):
        gui_print("ERROR: " + msg)


def ytdlp_progress_hook(d):
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        eta = d.get("eta")
        gui_print(f"[download] {percent} ETA {eta}s {speed}")

    elif d["status"] == "finished":
        gui_print("[download] Finished downloading source file")
        gui_print("[download] Post-processing...")


# ================================================================
#  HELPERS
# ================================================================
def is_local_file(path: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:\\", path))


def run_ffmpeg_streamed(cmd):
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
            gui_print(line.rstrip())

        p.wait()
        gui_print("✅ ffmpeg finished.")
    except Exception as e:
        gui_print(f"❌ ffmpeg error: {e}")


# ================================================================
#  FORMAT SUMMARY
# ================================================================
def summarize_best_format(info):
    if "requested_formats" in info:
        fmt = info["requested_formats"][0]
    else:
        fmt = info

    abr = fmt.get("abr")
    asr = fmt.get("asr")
    acodec = fmt.get("acodec")
    ext = fmt.get("ext")

    gui_print(
        f"🔍 Best format detected: {ext} • {acodec} • "
        f"{f'{abr} kbps' if abr else 'unknown bitrate'} • "
        f"{f'{asr} Hz' if asr else 'unknown sample rate'}"
    )


# ================================================================
#  CORE OPS
# ================================================================
def convert_to_mp3(input_file, output_folder):
    """Convert downloaded audio to MP3 using ffmpeg."""
    base = os.path.splitext(os.path.basename(input_file))[0]
    output_mp3 = os.path.join(output_folder, base + ".mp3")

    cmd = [
        FFMPEG_PATH,
        "-i",
        input_file,
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ab",
        "192k",
        output_mp3,
    ]

    gui_print(f"🎵 Converting to MP3 → {output_mp3}")
    run_ffmpeg_streamed(cmd)
    gui_print(f"✅ Saved MP3: {output_mp3}")


def download_youtube_audio(url: str, format_choice: str):
    global FFMPEG_PATH, OUTPUT_FOLDER

    gui_print(f"🎧 Downloading from YouTube: {url}")

    # If MP3 is chosen, we download bestaudio (any ext), then convert
    if format_choice == "mp3":
        ydl_format = "bestaudio/best"
    else:
        # webm explicitly chosen
        ydl_format = "bestaudio[ext=webm]/bestaudio"

    ydl_opts = {
        "format": ydl_format,
        "outtmpl": os.path.join(OUTPUT_FOLDER, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "ffmpeg_location": FFMPEG_PATH,
        "quiet": False,
        "verbose": True,
        "logger": GuiLogger(),
        "progress_hooks": [ytdlp_progress_hook],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # The downloaded file
    if "requested_downloads" in info:
        dl_file = info["requested_downloads"][0]["filepath"]
    else:
        dl_file = info["filepath"]

    summarize_best_format(info)

    if format_choice == "mp3":
        convert_to_mp3(dl_file, OUTPUT_FOLDER)

    gui_print(f"✅ Downloaded: {info.get('title', 'unknown')}")
    gui_print(f"📁 Saved to: {OUTPUT_FOLDER}")


# ================================================================
#  WORKER THREAD
# ================================================================
def worker(url_or_file, out_folder, audio_ext):
    global OUTPUT_FOLDER
    try:
        OUTPUT_FOLDER = out_folder
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)

        if not url_or_file:
            url_or_file = default_url

        if url_or_file.lower().startswith(("http://", "https://")):
            download_youtube_audio(url_or_file, audio_ext)

        elif is_local_file(url_or_file):
            gui_print("Local file conversion not changed.")
            # could extend to allow mp3 conversion here too

        else:
            gui_print("❌ Invalid input path or URL.")

    except Exception as e:
        gui_print(f"❌ Error: {e}")
    finally:
        log_queue.put("__DONE__")


def run_process():
    global RUNNING
    if RUNNING:
        return

    RUNNING = True
    ok_button.config(state="disabled")

    url_or_file = input_box.get().strip()
    out_folder = output_box.get().strip()
    audio_ext = audio_format_var.get()  # "mp3" or "webm"

    t = threading.Thread(
        target=worker,
        args=(url_or_file, out_folder, audio_ext),
        daemon=True,
    )
    t.start()


# ================================================================
#  CONFIG WINDOW
# ================================================================
def open_config_window():
    config_win = Toplevel(root)
    config_win.title("Location of FFmpeg")
    config_win.geometry("500x200")
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
            gui_print("❌ Invalid ffmpeg path.")

    tk.Button(config_win, text="Browse…", command=browse_ffmpeg).pack(pady=5)
    tk.Button(config_win, text="Save", width=12, command=save_config).pack(pady=10)


# ================================================================
#  GUI LAYOUT
# ================================================================
root = tk.Tk()
root.title("YouTube / MP3 / WebM Audio Downloader")
root.geometry("780x650")

# URL entry
tk.Label(root, text="YouTube URL or Local MP4 Path:").pack(anchor="w", padx=10, pady=(10, 0))
input_box = tk.Entry(root, width=100)
input_box.insert(0, default_url)
input_box.pack(padx=10, pady=5)

# Output folder
tk.Label(root, text="Output Folder:").pack(anchor="w", padx=10)
output_box = tk.Entry(root, width=100)
output_box.insert(0, OUTPUT_FOLDER)
output_box.pack(padx=10, pady=5)

# Audio format selection (mp3 or webm)
format_frame = tk.Frame(root)
format_frame.pack(pady=5, anchor="w", padx=10)

tk.Label(format_frame, text="Output Format:").pack(side="left")

audio_format_var = tk.StringVar(value="mp3")
tk.Radiobutton(format_frame, text=".mp3", variable=audio_format_var, value="mp3").pack(side="left", padx=10)
tk.Radiobutton(format_frame, text=".webm", variable=audio_format_var, value="webm").pack(side="left", padx=10)

# Buttons
button_frame = tk.Frame(root)
button_frame.pack(pady=15)

ok_button = tk.Button(button_frame, text="OK", width=20, command=run_process)
ok_button.grid(row=0, column=0, padx=10)

config_button = tk.Button(button_frame, text="Config", width=20, command=open_config_window)
config_button.grid(row=0, column=1, padx=10)

# Console
tk.Label(root, text="Status Console:").pack(anchor="w", padx=10)
console = scrolledtext.ScrolledText(root, width=100, height=22, bg="black", fg="lime", insertbackground="white")
console.configure(font=("Consolas", 10))
console.pack(padx=10, pady=5)
console.configure(state="disabled")

root.after(50, process_log_queue)
root.mainloop()
