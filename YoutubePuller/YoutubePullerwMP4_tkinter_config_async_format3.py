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

        if url_or_file.lower().startswith(("http://", "https://")):
            download_youtube_audio(url_or_file, audio_ext)
        else:
            gui_print("❌ Only URLs supported.")
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
#  CONFIG WINDOW (Wider, Centered, Inline Buttons)
# ================================================================
def open_config_window():
    config_win = Toplevel(root)
    config_win.title("Configuration")

    # Modal width & center
    width = 650
    height = 260
    config_win.geometry(f"{width}x{height}+{root.winfo_screenwidth()//2 - width//2}+{root.winfo_screenheight()//2 - height//2}")
    config_win.resizable(False, False)

    # FFmpeg Row
    row1 = tk.Frame(config_win)
    row1.pack(fill="x", padx=10, pady=(20, 10))

    tk.Label(row1, text="FFmpeg executable:", width=18, anchor="w").pack(side="left")

    ffmpeg_entry = tk.Entry(row1, width=60)
    ffmpeg_entry.pack(side="left", padx=4)
    ffmpeg_entry.insert(0, FFMPEG_PATH)

    def browse_ffmpeg():
        f = filedialog.askopenfilename(title="Select ffmpeg.exe", filetypes=[("ffmpeg", "ffmpeg.exe")])
        if f:
            ffmpeg_entry.delete(0, tk.END)
            ffmpeg_entry.insert(0, f)

    tk.Button(row1, text="Browse…", command=browse_ffmpeg).pack(side="left", padx=4)

    # Output Folder Row
    row2 = tk.Frame(config_win)
    row2.pack(fill="x", padx=10, pady=10)

    tk.Label(row2, text="Output Folder:", width=18, anchor="w").pack(side="left")

    output_entry = tk.Entry(row2, width=60)
    output_entry.pack(side="left", padx=4)
    output_entry.insert(0, OUTPUT_FOLDER)

    def browse_output():
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            output_entry.delete(0, tk.END)
            output_entry.insert(0, folder)

    tk.Button(row2, text="Browse…", command=browse_output).pack(side="left", padx=4)

    # Save Button
    tk.Button(config_win, text="Save Settings", width=16, command=lambda: save_config(config_win, ffmpeg_entry, output_entry)).pack(pady=20)


def save_config(win, ffmpeg_entry, output_entry):
    global FFMPEG_PATH, OUTPUT_FOLDER

    new_ffmpeg = ffmpeg_entry.get().strip()
    new_output = output_entry.get().strip()

    if not os.path.isfile(new_ffmpeg):
        gui_print("❌ Invalid ffmpeg path.")
        return

    if not os.path.isdir(new_output):
        gui_print("❌ Invalid output folder.")
        return

    FFMPEG_PATH = new_ffmpeg
    OUTPUT_FOLDER = new_output

    gui_print(f"✔ FFmpeg Updated:\n{FFMPEG_PATH}")
    gui_print(f"✔ Output Folder Updated:\n{OUTPUT_FOLDER}")

    win.destroy()


# ================================================================
#  MAIN UI LAYOUT
# ================================================================
root = tk.Tk()
root.title("YouTube / MP3 / WebM Audio Downloader")
root.geometry("820x650")

# Small config button in upper-right
config_btn = tk.Button(root, text="Config", width=8, command=open_config_window)
config_btn.place(relx=0.98, rely=0.01, anchor="ne")

# URL input
tk.Label(root, text="YouTube URL or Local MP4 Path:").pack(anchor="w", padx=10, pady=(10, 0))
input_box = tk.Entry(root, width=100)
input_box.insert(0, default_url)
input_box.pack(padx=10, pady=5)

# Output folder
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

# OK button moved to right side
ok_button = tk.Button(root, text="OK", width=14, command=run_process)
ok_button.place(relx=0.82, rely=0.23)

# Console
tk.Label(root, text="Status Console:").pack(anchor="w", padx=10)
console = scrolledtext.ScrolledText(root, width=100, height=22, bg="black", fg="lime", insertbackground="white", font=("Consolas", 10))
console.pack(padx=10, pady=5)
console.configure(state="disabled")

root.after(50, process_log_queue)
root.mainloop()
