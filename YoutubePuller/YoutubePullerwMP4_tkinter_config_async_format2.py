import os
import re
import subprocess
import threading
import tempfile
from queue import Queue

import yt_dlp
import tkinter as tk
from tkinter import scrolledtext, filedialog, Toplevel

# ================================================================
#  CONFIG DEFAULTS
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
#  YT-DLP LOGGER + PROGRESS HOOK
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
        gui_print("[download] Finished downloading source")


# ================================================================
#  HELPERS
# ================================================================
def is_local_file(path: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:\\", path))


def run_ffmpeg_streamed(cmd):
    gui_print("⚙️ Running ffmpeg...")

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
#  MP3 CONVERSION + TEMP CLEANUP
# ================================================================
def convert_to_mp3(input_temp_file, output_folder):
    base = os.path.splitext(os.path.basename(input_temp_file))[0]
    output_mp3 = os.path.join(output_folder, base + ".mp3")

    cmd = [
        FFMPEG_PATH, "-i", input_temp_file,
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "192k",
        output_mp3,
    ]

    gui_print(f"🎵 Converting to MP3 → {output_mp3}")
    run_ffmpeg_streamed(cmd)

    try:
        os.remove(input_temp_file)
        gui_print(f"🗑 Deleted temp file: {input_temp_file}")
    except Exception as e:
        gui_print(f"⚠ Could not delete temp file: {e}")

    gui_print(f"✅ Saved MP3: {output_mp3}")


# ================================================================
#  DOWNLOAD LOGIC
# ================================================================
def download_youtube_audio(url: str, output_format: str):
    global FFMPEG_PATH, OUTPUT_FOLDER

    gui_print(f"🎧 Downloading: {url}")

    if output_format == "mp3":
        temp_dir = tempfile.gettempdir()
        outtmpl = os.path.join(temp_dir, "%(title)s.%(ext)s")
        ydl_format = "bestaudio/best"
    else:
        outtmpl = os.path.join(OUTPUT_FOLDER, "%(title)s.%(ext)s")
        ydl_format = "bestaudio[ext=webm]/bestaudio"

    ydl_opts = {
        "format": ydl_format,
        "outtmpl": outtmpl,
        "noplaylist": True,
        "ffmpeg_location": FFMPEG_PATH,
        "logger": GuiLogger(),
        "progress_hooks": [ytdlp_progress_hook],
        "verbose": True,
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    summarize_best_format(info)

    if "requested_downloads" in info:
        dl_file = info["requested_downloads"][0]["filepath"]
    else:
        dl_file = info["filepath"]

    if output_format == "mp3":
        convert_to_mp3(dl_file, OUTPUT_FOLDER)
    else:
        gui_print(f"🎵 Saved WEBM: {dl_file}")

    gui_print(f"📁 Final Output Folder: {OUTPUT_FOLDER}")


# ================================================================
#  WORKER THREAD
# ================================================================
def worker(url_or_file, out_folder, audio_ext):
    global OUTPUT_FOLDER

    try:
        OUTPUT_FOLDER = out_folder
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)

        if url_or_file.lower().startswith(("http://","https://")):
            download_youtube_audio(url_or_file, audio_ext)
        else:
            gui_print("❌ Only YouTube URLs currently supported.")
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
    format_choice = audio_format_var.get()

    t = threading.Thread(
        target=worker, args=(url_or_file, out_folder, format_choice), daemon=True
    )
    t.start()


# ================================================================
#  CONFIG WINDOW (NEW: OUTPUT FOLDER ADDED)
# ================================================================
def open_config_window():
    config_win = Toplevel(root)
    config_win.title("Configuration")
    config_win.geometry("550x260")
    config_win.resizable(False, False)

    # -------------------
    # FFmpeg section
    # -------------------
    tk.Label(config_win, text="FFmpeg executable:").pack(anchor="w", padx=10, pady=(8,0))

    ffmpeg_entry = tk.Entry(config_win, width=70)
    ffmpeg_entry.insert(0, FFMPEG_PATH)
    ffmpeg_entry.pack(padx=10, pady=4)

    def browse_ffmpeg():
        f = filedialog.askopenfilename(
            title="Select ffmpeg.exe",
            filetypes=[("ffmpeg", "ffmpeg.exe"), ("All Files", "*.*")]
        )
        if f:
            ffmpeg_entry.delete(0, tk.END)
            ffmpeg_entry.insert(0, f)

    tk.Button(config_win, text="Browse FFmpeg…", command=browse_ffmpeg).pack(pady=3)

    # -------------------
    # Output folder section (NEW)
    # -------------------
    tk.Label(config_win, text="Output Folder:").pack(anchor="w", padx=10, pady=(12,0))

    output_entry = tk.Entry(config_win, width=70)
    output_entry.insert(0, OUTPUT_FOLDER)
    output_entry.pack(padx=10, pady=4)

    def browse_output():
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            output_entry.delete(0, tk.END)
            output_entry.insert(0, folder)

    tk.Button(config_win, text="Browse Folder…", command=browse_output).pack(pady=3)

    # -------------------
    # Save button
    # -------------------
    def save():
        global FFMPEG_PATH, OUTPUT_FOLDER

        f = ffmpeg_entry.get().strip()
        o = output_entry.get().strip()

        if not os.path.isfile(f):
            gui_print("❌ Invalid ffmpeg.exe path.")
            return
        if not os.path.isdir(o):
            gui_print("❌ Invalid output directory.")
            return

        FFMPEG_PATH = f
        OUTPUT_FOLDER = o

        gui_print(f"✔ FFmpeg updated:\n{FFMPEG_PATH}")
        gui_print(f"✔ Output folder updated:\n{OUTPUT_FOLDER}")

        config_win.destroy()

    tk.Button(config_win, text="Save Settings", width=20, command=save).pack(pady=18)


# ================================================================
#  GUI LAYOUT
# ================================================================
root = tk.Tk()
root.title("YouTube → MP3 / WebM Downloader")
root.geometry("800x650")

tk.Label(root, text="YouTube URL:").pack(anchor="w", padx=10, pady=(10,0))
input_box = tk.Entry(root, width=100)
input_box.insert(0, default_url)
input_box.pack(padx=10, pady=5)

tk.Label(root, text="Output Folder:").pack(anchor="w", padx=10)
output_box = tk.Entry(root, width=100)
output_box.insert(0, OUTPUT_FOLDER)
output_box.pack(padx=10, pady=5)

# Format selection
format_frame = tk.Frame(root)
format_frame.pack(anchor="w", padx=10, pady=5)

tk.Label(format_frame, text="Output Format:").pack(side="left")

audio_format_var = tk.StringVar(value="mp3")
tk.Radiobutton(format_frame, text=".mp3", value="mp3", variable=audio_format_var).pack(side="left", padx=10)
tk.Radiobutton(format_frame, text=".webm", value="webm", variable=audio_format_var).pack(side="left", padx=10)

# Buttons
btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

ok_button = tk.Button(btn_frame, text="OK", width=20, command=run_process)
ok_button.grid(row=0, column=0, padx=10)

tk.Button(btn_frame, text="Config", width=20, command=open_config_window).grid(row=0, column=1, padx=10)

# Console
tk.Label(root, text="Status Console:").pack(anchor="w", padx=10)
console = scrolledtext.ScrolledText(
    root, width=100, height=22, bg="black", fg="lime",
    insertbackground="white", font=("Consolas", 10)
)
console.pack(padx=10, pady=5)
console.configure(state="disabled")

root.after(50, process_log_queue)
root.mainloop()
