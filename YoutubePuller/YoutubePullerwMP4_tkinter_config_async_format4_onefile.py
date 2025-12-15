import os
import sys
import re
import subprocess
import threading
import tempfile
import configparser
from queue import Queue

import yt_dlp
import tkinter as tk
from tkinter import scrolledtext, filedialog, Toplevel

# ================================================================
#  ENSURE settings.ini EXISTS WITH DEFAULTS
# ================================================================
DEFAULT_INI_CONTENT = """
[config]
ffmpeg_path = d:\\ffmpeg\\bin\\ffmpeg.exe
output_folder = d:\\temp\\youtubeaudiooutput
os = windows
"""

INI_PATH = "settings.ini"

# If packaged, store ini next to EXE
if getattr(sys, "frozen", False):
    INI_PATH = os.path.join(os.path.dirname(sys.executable), "settings.ini")

# Auto-create if missing
if not os.path.exists(INI_PATH):
    with open(INI_PATH, "w", encoding="utf-8") as f:
        f.write(DEFAULT_INI_CONTENT.strip())

# ================================================================
#  RESOURCE PATH (for PyInstaller --onefile)
# ================================================================
def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)

# ================================================================
#  LOAD SETTINGS.INI
# ================================================================
config = configparser.ConfigParser()
config.read(INI_PATH)

FFMPEG_PATH = config.get("config", "ffmpeg_path", fallback=r"d:\ffmpeg\bin\ffmpeg.exe")
OUTPUT_FOLDER = config.get("config", "output_folder", fallback=r"d:\temp\youtubeaudiooutput")
APP_OS = config.get("config", "os", fallback="windows")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
default_url = "https://www.youtube.com/watch?v=qmlYf5d-Cvo"

log_queue = Queue()
RUNNING = False

# ================================================================
#  GUI LOGGING SYSTEM
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
#  YT-DLP LOGGER + PROGRESS CALLBACKS
# ================================================================
class GuiLogger:
    def debug(self, msg): gui_print(msg)
    def info(self, msg): gui_print(msg)
    def warning(self, msg): gui_print("WARNING: " + msg)
    def error(self, msg): gui_print("ERROR: " + msg)

def ytdlp_progress_hook(d):
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        eta = d.get("eta")
        gui_print(f"[download] {percent} ETA {eta}s {speed}")
    elif d["status"] == "finished":
        gui_print("[download] Finished downloading source file")

# ================================================================
#  HELPER FUNCTIONS
# ================================================================
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
#  MP3 CONVERSION
# ================================================================
def convert_to_mp3(input_temp, output_dir):
    base = os.path.splitext(os.path.basename(input_temp))[0]
    output_mp3 = os.path.join(output_dir, base + ".mp3")

    cmd = [
        FFMPEG_PATH, "-i", input_temp,
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "192k",
        output_mp3,
    ]

    gui_print(f"🎵 Converting to MP3 → {output_mp3}")
    run_ffmpeg_streamed(cmd)

    try:
        os.remove(input_temp)
        gui_print(f"🗑 Deleted temp file: {input_temp}")
    except Exception as e:
        gui_print(f"⚠ Could not delete temp file: {e}")

    gui_print(f"✅ Saved MP3: {output_mp3}")

# ================================================================
#  DOWNLOAD AUDIO USING YT-DLP
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
        src_file = info["requested_downloads"][0]["filepath"]
    else:
        src_file = info["filepath"]

    if output_format == "mp3":
        convert_to_mp3(src_file, OUTPUT_FOLDER)
    else:
        gui_print(f"🎵 Saved WEBM: {src_file}")

    gui_print(f"📁 Final Output Folder: {OUTPUT_FOLDER}")

# ================================================================
#  THREAD WORKER
# ================================================================
def worker(url, out_folder, ext):
    global OUTPUT_FOLDER
    try:
        OUTPUT_FOLDER = out_folder
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)

        if url.lower().startswith(("http://", "https://")):
            download_youtube_audio(url, ext)
        else:
            gui_print("❌ Only URLs are supported.")
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

    url = input_box.get().strip()
    out = output_box.get().strip()
    ext = audio_format_var.get()

    threading.Thread(target=worker, args=(url, out, ext), daemon=True).start()

# ================================================================
#  CONFIGURATION WINDOW
# ================================================================
def open_config_window():
    global APP_OS

    win = Toplevel(root)
    win.title("Configuration")

    width = 650
    height = 320
    win.geometry(
        f"{width}x{height}+"
        f"{root.winfo_screenwidth()//2 - width//2}+"
        f"{root.winfo_screenheight()//2 - height//2}"
    )
    win.resizable(False, False)

    # OS Selection
    os_frame = tk.Frame(win)
    os_frame.pack(fill="x", padx=10, pady=(15, 8))

    tk.Label(os_frame, text="Operating System:", width=18, anchor="w").pack(side="left")
    os_var = tk.StringVar(value=APP_OS)

    rb_win = tk.Radiobutton(os_frame, text="Windows", value="windows", variable=os_var)
    rb_mac = tk.Radiobutton(os_frame, text="Mac", value="mac", variable=os_var)
    rb_win.pack(side="left", padx=10)
    rb_mac.pack(side="left", padx=10)

    # FFmpeg Row
    row1 = tk.Frame(win)
    row1.pack(fill="x", padx=10, pady=10)

    tk.Label(row1, text="FFmpeg executable:", width=18, anchor="w").pack(side="left")

    ffmpeg_entry = tk.Entry(row1, width=60)
    ffmpeg_entry.pack(side="left", padx=4)
    ffmpeg_entry.insert(0, FFMPEG_PATH)

    btn_ff = tk.Button(row1, text="Browse…", command=lambda: browse_ffmpeg(ffmpeg_entry))
    btn_ff.pack(side="left", padx=4)

    # Output Folder Row
    row2 = tk.Frame(win)
    row2.pack(fill="x", padx=10, pady=10)

    tk.Label(row2, text="Output Folder:", width=18, anchor="w").pack(side="left")

    output_entry = tk.Entry(row2, width=60)
    output_entry.pack(side="left", padx=4)
    output_entry.insert(0, OUTPUT_FOLDER)

    btn_out = tk.Button(row2, text="Browse…", command=lambda: browse_output(output_entry))
    btn_out.pack(side="left", padx=4)

    # Enable / disable fields based on OS mode
    def update_os_mode():
        mode = os_var.get()
        if mode == "mac":
            ffmpeg_entry.config(state="disabled")
            output_entry.config(state="disabled")
            btn_ff.config(state="disabled")
            btn_out.config(state="disabled")
        else:
            ffmpeg_entry.config(state="normal")
            output_entry.config(state="normal")
            btn_ff.config(state="normal")
            btn_out.config(state="normal")

    rb_win.config(command=update_os_mode)
    rb_mac.config(command=update_os_mode)
    update_os_mode()

    # Save button
    tk.Button(
        win, text="Save Settings", width=16,
        command=lambda: save_config(win, ffmpeg_entry, output_entry, os_var)
    ).pack(pady=20)

# Config Helpers
def browse_ffmpeg(entry):
    f = filedialog.askopenfilename(title="Select ffmpeg", filetypes=[("All Files", "*.*")])
    if f:
        entry.delete(0, tk.END)
        entry.insert(0, f)

def browse_output(entry):
    f = filedialog.askdirectory(title="Select Output Folder")
    if f:
        entry.delete(0, tk.END)
        entry.insert(0, f)

def save_config(win, ffmpeg_entry, output_entry, os_var):
    global FFMPEG_PATH, OUTPUT_FOLDER, APP_OS

    APP_OS = os_var.get()

    if APP_OS == "windows":
        ff = ffmpeg_entry.get().strip()
        out = output_entry.get().strip()

        if not os.path.isfile(ff):
            gui_print("❌ Invalid ffmpeg path.")
            return
        if not os.path.isdir(out):
            gui_print("❌ Invalid output directory.")
            return

        FFMPEG_PATH = ff
        OUTPUT_FOLDER = out

    cfg = configparser.ConfigParser()
    cfg["config"] = {
        "ffmpeg_path": FFMPEG_PATH,
        "output_folder": OUTPUT_FOLDER,
        "os": APP_OS,
    }

    with open(INI_PATH, "w") as f:
        cfg.write(f)

    gui_print(f"✔ Saved settings → {INI_PATH}")
    win.destroy()

# ================================================================
#  MAIN WINDOW
# ================================================================
root = tk.Tk()
root.title("YouTube → MP3 / WebM  Downloader")
root.geometry("820x650")

# Config button (upper-right)
config_btn = tk.Button(root, text="Config", width=8, command=open_config_window)
config_btn.place(relx=0.98, rely=0.01, anchor="ne")

# URL Entry
tk.Label(root, text="YouTube URL or Local MP4 Path:").pack(anchor="w", padx=10, pady=(10, 0))
input_box = tk.Entry(root, width=100)
input_box.insert(0, default_url)
input_box.pack(padx=10, pady=5)

# Output folder
tk.Label(root, text="Output Folder:").pack(anchor="w", padx=10)
output_box = tk.Entry(root, width=100)
output_box.insert(0, OUTPUT_FOLDER)
output_box.pack(padx=10, pady=5)

# Output format radio buttons
format_frame = tk.Frame(root)
format_frame.pack(anchor="w", padx=10, pady=5)
tk.Label(format_frame, text="Output Format:").pack(side="left")
audio_format_var = tk.StringVar(value="mp3")
tk.Radiobutton(format_frame, text=".mp3", value="mp3", variable=audio_format_var).pack(side="left", padx=10)
tk.Radiobutton(format_frame, text=".webm", value="webm", variable=audio_format_var).pack(side="left", padx=10)

# OK button bottom-right
ok_button = tk.Button(root, text="OK", width=14, command=run_process)
ok_button.place(relx=0.98, rely=0.95, anchor="se")

# Console box
tk.Label(root, text="Status Console:").pack(anchor="w", padx=10)
console = scrolledtext.ScrolledText(
    root, width=100, height=22, bg="black", fg="lime",
    insertbackground="white", font=("Consolas", 10)
)
console.pack(padx=10, pady=5)
console.configure(state="disabled")

root.after(50, process_log_queue)
root.mainloop()
