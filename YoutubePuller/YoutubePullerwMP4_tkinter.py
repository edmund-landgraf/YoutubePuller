import yt_dlp
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import scrolledtext, filedialog

FFMPEG_PATH = r"d:\ffmpeg\bin\ffmpeg.exe"
OUTPUT_FOLDER = r"d:\temp\youtubeaudiooutput"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------
def gui_print(msg: str):
    """
    Print to the on-screen console.
    """
    console.configure(state="normal")
    console.insert(tk.END, msg + "\n")
    console.see(tk.END)
    console.configure(state="disabled")


def is_local_file(path: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:\\", path))


def convert_local_mp4_to_mp3(filepath: str):
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
        output_mp3
    ]

    gui_print(f"🎵 Converting local file → {output_mp3}")
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    gui_print(f"✅ MP3 saved: {output_mp3}")


def download_youtube_audio(url: str):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(OUTPUT_FOLDER, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "ffmpeg_location": FFMPEG_PATH,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
    }

    gui_print(f"🎧 Downloading from YouTube: {url}\n")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    gui_print(f"✅ Downloaded: {info.get('title', 'unknown')}")
    gui_print(f"📁 Saved to: {OUTPUT_FOLDER}")


# -------------------------------------------------------------------
# MAIN OPERATION
# -------------------------------------------------------------------
def run_process():
    url_or_file = input_box.get().strip()
    out_folder = output_box.get().strip()

    # sync output folder with global logic
    global OUTPUT_FOLDER
    OUTPUT_FOLDER = out_folder
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    if not url_or_file:
        url_or_file = default_url

    if url_or_file.lower().startswith("http://") or url_or_file.lower().startswith("https://"):
        download_youtube_audio(url_or_file)

    elif is_local_file(url_or_file):
        convert_local_mp4_to_mp3(url_or_file)

    else:
        gui_print("❌ Input must be a YouTube URL (http/https) or a local .mp4 file.")


# -------------------------------------------------------------------
# TKINTER UI
# -------------------------------------------------------------------
root = tk.Tk()
root.title("YouTube / MP4 → MP3 Converter")
root.geometry("700x500")

default_url = "http://youtube.com/watch?v=qmlYf5d-Cvo&list=RDqmlYf5d-Cvo&start_radio=1"

tk.Label(root, text="YouTube URL or Local MP4 Path:").pack(anchor="w", padx=10, pady=(10, 0))
input_box = tk.Entry(root, width=90)
input_box.insert(0, default_url)
input_box.pack(padx=10, pady=5)

tk.Label(root, text="Output Folder:").pack(anchor="w", padx=10)
output_box = tk.Entry(root, width=90)
output_box.insert(0, OUTPUT_FOLDER)
output_box.pack(padx=10, pady=5)

ok_button = tk.Button(root, text="OK", width=20, command=run_process)
ok_button.pack(pady=10)

tk.Label(root, text="Status Console:").pack(anchor="w", padx=10)

console = scrolledtext.ScrolledText(root, width=90, height=15, bg="black", fg="lime", insertbackground="white")
console.configure(font=("Consolas", 10))
console.pack(padx=10, pady=5)
console.configure(state="disabled")

root.mainloop()
