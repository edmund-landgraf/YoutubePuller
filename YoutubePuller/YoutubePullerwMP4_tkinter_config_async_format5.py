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
#  GLOBAL CONFIG DEFAULTS
# ================================================================
FFMPEG_PATH = r"d:\ffmpeg\bin\ffmpeg.exe"
OUTPUT_FOLDER = r"d:\temp\youtubeaudiooutput"
APP_OS = "windows"  # NEW GLOBAL FLAG

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

default_url = "https://www.youtube.com/watch?v=qmlYf5d-Cvo"

log_queue = Queue()
RUNNING = False


# ================================================================
#  LOGGING INTO GUI
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
        gui_print("[download] Finished downloading source file")


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
#  MP3 CONVERSION (TEMP CLEANUP)
# ================================================================
def convert_to_mp3(input_temp_file, output_folder):
    base = os.path.splitext(os.path.basename(input_temp_file))[0]
    output_mp3 = os.path.join(output_folder, base + ".mp3")

    # cmd = [
    #     FFMPEG_PATH, "-i", input_temp_file,
    #     "-vn",
    #     "-acodec", "libmp3lame",
    #     "-ab", "192k",
    #     output_mp3,
    # ]
    cmd = [
        FFMPEG_PATH,
        "-y",                      # ← THIS IS THE FIX
        "-i", input_temp_file,
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
#  THREAD WORKER
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

# Helpers
def normalize_and_validate_input(raw_input: str):
    s = raw_input.strip()

    # Add https:// if missing but looks like YouTube
    if s.startswith("www.youtube.com") or s.startswith("youtube.com"):
        s = "https://" + s

    # YouTube URL validation
    youtube_regex = re.compile(
        r"^https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]+"
    )

    if youtube_regex.match(s):
        return s, "youtube"

    # Local MP4 validation
    if os.path.isfile(s) and s.lower().endswith(".mp4"):
        return s, "mp4"

    return None, None

def run_process():
    global RUNNING
    if RUNNING:
        return

    RUNNING = True
    ok_button.config(state="disabled")

    # url_or_file = input_box.get().strip()
    raw_input = input_box.get().strip()
    url_or_file, input_type = normalize_and_validate_input(raw_input)

    if not url_or_file:
        gui_print("❌ Invalid input. Enter a YouTube URL or a local .mp4 file.")
        RUNNING = False
        ok_button.config(state="normal")
        return

    out_folder = output_box.get().strip()
    format_choice = audio_format_var.get()

    threading.Thread(
        target=worker, args=(url_or_file, out_folder, format_choice), daemon=True
    ).start()


# ================================================================
#  CONFIG WINDOW (WITH WINDOWS/MAC RADIO)
# ================================================================
def open_config_window():
    global APP_OS

    config_win = Toplevel(root)
    config_win.title("Configuration")

    width = 650
    height = 320
    config_win.geometry(
        f"{width}x{height}+"
        f"{root.winfo_screenwidth()//2 - width//2}+"
        f"{root.winfo_screenheight()//2 - height//2}"
    )
    config_win.resizable(False, False)

    # ---------------------------
    # OS Selection Row (NEW)
    # ---------------------------
    os_frame = tk.Frame(config_win)
    os_frame.pack(fill="x", padx=10, pady=(15, 8))

    tk.Label(os_frame, text="Operating System:", width=18, anchor="w").pack(side="left")

    os_var = tk.StringVar(value=APP_OS)
    rb_win = tk.Radiobutton(os_frame, text="Windows", value="windows", variable=os_var)
    rb_mac = tk.Radiobutton(os_frame, text="Mac", value="mac", variable=os_var)

    rb_win.pack(side="left", padx=10)
    rb_mac.pack(side="left", padx=10)

    # ---------------------------
    # FFmpeg Row
    # ---------------------------
    row1 = tk.Frame(config_win)
    row1.pack(fill="x", padx=10, pady=10)

    tk.Label(row1, text="FFmpeg executable:", width=18, anchor="w").pack(side="left")

    ffmpeg_entry = tk.Entry(row1, width=60)
    ffmpeg_entry.pack(side="left", padx=4)
    ffmpeg_entry.insert(0, FFMPEG_PATH)

    btn_ff = tk.Button(row1, text="Browse…", command=lambda: browse_ffmpeg(ffmpeg_entry))
    btn_ff.pack(side="left", padx=4)

    # ---------------------------
    # Output folder row
    # ---------------------------
    row2 = tk.Frame(config_win)
    row2.pack(fill="x", padx=10, pady=10)

    tk.Label(row2, text="Output Folder:", width=18, anchor="w").pack(side="left")

    output_entry = tk.Entry(row2, width=60)
    output_entry.pack(side="left", padx=4)
    output_entry.insert(0, OUTPUT_FOLDER)

    btn_out = tk.Button(row2, text="Browse…", command=lambda: browse_output(output_entry))
    btn_out.pack(side="left", padx=4)

    # ---------------------------
    # OS MODE HANDLER
    # ---------------------------
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

    # ---------------------------
    # SAVE BUTTON
    # ---------------------------
    tk.Button(
        config_win, text="Save Settings", width=16,
        command=lambda: save_config(config_win, ffmpeg_entry, output_entry, os_var)
    ).pack(pady=20)


def browse_ffmpeg(entry):
    f = filedialog.askopenfilename(title="Select ffmpeg", filetypes=[("All", "*")])
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
        ffmpeg = ffmpeg_entry.get().strip()
        out = output_entry.get().strip()

        if not os.path.isfile(ffmpeg):
            gui_print("❌ Invalid ffmpeg path.")
            return

        if not os.path.isdir(out):
            gui_print("❌ Invalid output directory.")
            return

        FFMPEG_PATH = ffmpeg
        OUTPUT_FOLDER = out

    gui_print(f"✔ OS mode: {APP_OS}")
    gui_print(f"✔ FFmpeg: {FFMPEG_PATH}")
    gui_print(f"✔ Output folder: {OUTPUT_FOLDER}")

    win.destroy()


# ================================================================
#  MAIN UI LAYOUT
# ================================================================
root = tk.Tk()
root.title("YouTube / MP3 / WebM Audio Downloader")
root.geometry("820x650")

# Config button (upper-right)
config_btn = tk.Button(root, text="Config", width=8, command=open_config_window)
config_btn.place(relx=0.98, rely=0.01, anchor="ne")

tk.Label(root, text="YouTube URL or Local MP4 Path:").pack(anchor="w", padx=10, pady=(10, 0))
input_box = tk.Entry(root, width=100)
input_box.insert(0, default_url)
input_box.pack(padx=10, pady=5)

tk.Label(root, text="Output Folder:").pack(anchor="w", padx=10)
output_box = tk.Entry(root, width=100)
output_box.insert(0, OUTPUT_FOLDER)
output_box.pack(padx=10, pady=5)

format_frame = tk.Frame(root)
format_frame.pack(anchor="w", padx=10, pady=5)

tk.Label(format_frame, text="Output Format:").pack(side="left")
audio_format_var = tk.StringVar(value="mp3")
tk.Radiobutton(format_frame, text=".mp3", value="mp3", variable=audio_format_var).pack(side="left", padx=10)
tk.Radiobutton(format_frame, text=".webm", value="webm", variable=audio_format_var).pack(side="left", padx=10)

# OK button AFTER the console — lower right corner
ok_button = tk.Button(root, text="OK", width=14, command=run_process)
ok_button.place(relx=0.98, rely=0.95, anchor="se")

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
