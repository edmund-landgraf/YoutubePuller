import yt_dlp
import yt_dlp.utils
import os
import re
import subprocess
import tkinter as tk
from tkinter import scrolledtext, filedialog, Toplevel

# -------------------------------------------------------------------
# DEFAULT CONFIG VALUES
# -------------------------------------------------------------------
FFMPEG_PATH = r"d:\ffmpeg\bin\ffmpeg.exe"
OUTPUT_FOLDER = r"d:\temp\youtubeaudiooutput"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# -------------------------------------------------------------------
# GUI PRINT (NEW: supports streamed lines)
# -------------------------------------------------------------------
def gui_print(msg: str):
    console.configure(state="normal")
    console.insert(tk.END, msg.rstrip() + "\n")
    console.see(tk.END)
    console.configure(state="disabled")


# -------------------------------------------------------------------
# CAPTURE yt_dlp logs (BIG FEATURE)
# -------------------------------------------------------------------
def patch_yt_dlp_logging():
    """
    Override yt_dlp’s stdout/stderr so every log line goes to the GUI.
    """

    def gui_stdout_write(s):
        gui_print(s)

    def gui_stderr_write(s):
        gui_print(s)

    yt_dlp.utils.stdout_write = gui_stdout_write
    yt_dlp.utils.stderr_write = gui_stderr_write
    yt_dlp.utils.std_print = gui_print


patch_yt_dlp_logging()


# -------------------------------------------------------------------
# UTILS
# -------------------------------------------------------------------
def is_local_file(path: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:\\", path))


# -------------------------------------------------------------------
# STREAMED FFMPEG EXECUTION (NEW)
# -------------------------------------------------------------------
def run_ffmpeg_streamed(cmd):
    """
    Runs ffmpeg with real-time output into the GUI console.
    """
    gui_print("⚙️ Running ffmpeg...")

    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    # Stream output line by line
    for line in p.stdout:
        gui_print(line)

    p.wait()
    gui_print("✅ ffmpeg completed.\n")


# -------------------------------------------------------------------
# MP4 → MP3 Conversion
# -------------------------------------------------------------------
def convert_local_mp4_to_mp3(filepath: str):
    global FFMPEG_PATH

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
        "-i", filepath,
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "192k",
        output_mp3,
    ]

    gui_print(f"🎵 Converting local file → {output_mp3}")
    run_ffmpeg_streamed(cmd)

    gui_print(f"✅ MP3 saved: {output_mp3}")


# -------------------------------------------------------------------
# YOUTUBE DOWNLOAD WITH FULL LOGS
# -------------------------------------------------------------------
def download_youtube_audio(url: str):
    global FFMPEG_PATH

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_FOLDER, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "ffmpeg_location": FFMPEG_PATH,
        "quiet": False,         # REQUIRED or yt_dlp logs won't appear
        "verbose": True,        # Force verbose log output
    }

    gui_print(f"🎧 Downloading from YouTube: {url}\n")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    gui_print(f"✅ Downloaded: {info.get('title', 'unknown')}")
    gui_print(f"📁 Saved to: {OUTPUT_FOLDER}\n")


# -------------------------------------------------------------------
# RUN PROCESS
# -------------------------------------------------------------------
def run_process():
    global OUTPUT_FOLDER

    url_or_file = input_box.get().strip()
    out_folder = output_box.get().strip()

    OUTPUT_FOLDER = out_folder
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    if not url_or_file:
        url_or_file = default_url

    if url_or_file.lower().startswith(("http://", "https://")):
        download_youtube_audio(url_or_file)

    elif is_local_file(url_or_file):
        convert_local_mp4_to_mp3(url_or_file)

    else:
        gui_print("❌ Input must be a YouTube URL or a local .mp4 file.")


# -------------------------------------------------------------------
# CONFIG MODAL
# -------------------------------------------------------------------
def open_config_window():
    config_win = Toplevel(root)
    config_win.title("Location of FFmpeg")
    config_win.geometry("500x180")
    config_win.resizable(False, False)

    tk.Label(config_win, text="FFmpeg executable location:").pack(anchor="w", padx=10, pady=(10, 0))

    ffmpeg_entry = tk.Entry(config_win, width=60)
    ffmpeg_entry.insert(0, FFMPEG_PATH)
    ffmpeg_entry.pack(padx=10, pady=5)

    def browse_ffmpeg():
        file_path = filedialog.askopenfilename(
            title="Select ffmpeg.exe",
            filetypes=[("FFmpeg Executable", "ffmpeg.exe"), ("All Files", "*.*")]
        )
        if file_path:
            ffmpeg_entry.delete(0, tk.END)
            ffmpeg_entry.insert(0, file_path)

    def save_config():
        global FFMPEG_PATH
        new_path = ffmpeg_entry.get().strip()
        if os.path.isfile(new_path):
            FFMPEG_PATH = new_path
            gui_print(f"⚙️ FFmpeg path updated:\n{FFMPEG_PATH}\n")
            config_win.destroy()
        else:
            gui_print("❌ Invalid FFmpeg path selected.")

    browse_btn = tk.Button(config_win, text="Browse…", command=browse_ffmpeg)
    browse_btn.pack(pady=5)

    save_btn = tk.Button(config_win, text="Save", width=12, command=save_config)
    save_btn.pack(pady=10)


# -------------------------------------------------------------------
# TK UI
# -------------------------------------------------------------------
root = tk.Tk()
root.title("YouTube / MP4 → MP3 Converter")
root.geometry("760x580")

default_url = "https://www.youtube.com/watch?v=qmlYf5d-Cvo"

tk.Label(root, text="YouTube URL or Local MP4 Path:").pack(anchor="w", padx=10, pady=(10, 0))
input_box = tk.Entry(root, width=100)
input_box.insert(0, default_url)
input_box.pack(padx=10, pady=5)

tk.Label(root, text="Output Folder:").pack(anchor="w", padx=10)
output_box = tk.Entry(root, width=100)
output_box.insert(0, OUTPUT_FOLDER)
output_box.pack(padx=10, pady=5)

# Buttons row
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

root.mainloop()
