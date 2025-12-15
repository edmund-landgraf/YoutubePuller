import yt_dlp
import os
import re
import subprocess
import sys

FFMPEG_PATH = r"d:\ffmpeg\bin\ffmpeg.exe"
OUTPUT_FOLDER = r"d:\temp\youtubeaudiooutput"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def is_local_file(path: str) -> bool:
    """
    Returns True if the input looks like a Windows drive path:  C:\..., D:\...
    """
    return bool(re.match(r"^[A-Za-z]:\\", path))


def convert_local_mp4_to_mp3(filepath: str):
    """
    Converts a local .mp4 file to .mp3 using ffmpeg.
    """
    if not os.path.isfile(filepath):
        print(f"❌ File does not exist: {filepath}")
        return

    if not filepath.lower().endswith(".mp4"):
        print("❌ Only .mp4 files are supported for local conversion.")
        return

    filename = os.path.splitext(os.path.basename(filepath))[0]
    output_mp3 = os.path.join(OUTPUT_FOLDER, f"{filename}.mp3")

    cmd = [
        FFMPEG_PATH,
        "-i", filepath,
        "-vn",            # no video
        "-acodec", "libmp3lame",
        "-ab", "192k",
        output_mp3
    ]

    print(f"🎵 Converting local file → {output_mp3}")
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print(f"✅ MP3 saved: {output_mp3}")


def download_youtube_audio(url: str):
    """
    Downloads the audio from a YouTube URL and saves it as MP3.
    """

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

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    print(f"\n✅ Downloaded: {info.get('title', 'unknown')}")
    print(f"📁 Saved to: {OUTPUT_FOLDER}")


if __name__ == "__main__":
    default_url = "http://youtube.com/watch?v=qmlYf5d-Cvo&list=RDqmlYf5d-Cvo&start_radio=1"
    user_input = input("Enter YouTube URL or a local MP4 file: ").strip()

    if not user_input:
        user_input = default_url

    # Case 1: YouTube URL
    if user_input.lower().startswith("http://") or user_input.lower().startswith("https://"):
        print(f"\n🎧 Downloading from YouTube: {user_input}\n")
        download_youtube_audio(user_input)

    # Case 2: Local mp4 file
    elif is_local_file(user_input):
        print(f"\n📂 Local file detected: {user_input}")
        convert_local_mp4_to_mp3(user_input)

    else:
        print("❌ Input must be a YouTube URL (http/https) or a local .mp4 file (C:\\path...).")
