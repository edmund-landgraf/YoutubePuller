import yt_dlp
import os

def download_youtube_audio(url: str):
    """
    Downloads the audio from a YouTube URL and saves it as MP3 (preserving best source quality).
    """

    # Define paths
    ffmpeg_path = r"d:\ffmpeg\bin\ffmpeg.exe"
    output_folder = r"d:\temp\youtubeaudiooutput"

    # Ensure the output directory exists
    os.makedirs(output_folder, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",             # Get the best available audio
        "outtmpl": os.path.join(output_folder, "%(title)s.%(ext)s"),
        "noplaylist": True,                     # Single video only
        "ffmpeg_location": ffmpeg_path,         # Explicit ffmpeg path
        "postprocessors": [
            {                                   # Convert to MP3
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,                         # Set True to suppress console output
        "progress_hooks": [
            lambda d: print(f"Status: {d['status']} - {d.get('filename', '')}")
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        print(f"\n✅ Downloaded: {info.get('title', 'unknown')}")
        print(f"📁 Saved to: {output_folder}")

if __name__ == "__main__":
    #default_url = "https://www.youtube.com/watch?v=bqH-GKVyryM"
    default_url = "http://youtube.com/watch?v=qmlYf5d-Cvo&list=RDqmlYf5d-Cvo&start_radio=1"
    youtube_url = input(f"Enter YouTube URL (or press Enter for default): ").strip()
    if not youtube_url:
        youtube_url = default_url

    print(f"\n🎧 Downloading from: {youtube_url}\n")
    download_youtube_audio(youtube_url)
