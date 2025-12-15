import yt_dlp
import os
import sys
import configparser

# =============================================================
#  📁 DOWNLOAD PATH HELPERS
# =============================================================

def get_downloads_path():
    """Return the current user's Downloads folder."""
    return os.path.join(os.environ["USERPROFILE"], "Downloads")

# =============================================================
#  📄 CONFIGURATION HANDLER
# =============================================================

def load_config(config_file="YoutubePuller.ini"):
    """
    Loads or creates YoutubePuller.ini with a dynamic %DOWNLOADPATH% variable.
    Expands any environment variables when loading values.
    """
    # Disable interpolation to allow literal % symbols
    config = configparser.ConfigParser(interpolation=None)

    if not os.path.exists(config_file):
        os.environ["DOWNLOADPATH"] = get_downloads_path()

        config["DEFAULTS"] = {
            "ffmpeg_path": r"d:\ffmpeg\bin\ffmpeg.exe",
            "default_url": "https://www.youtube.com/watch?v=bqH-GKVyryM",
            "default_output_folder": "%DOWNLOADPATH%"
        }

        with open(config_file, "w", encoding="utf-8") as f:
            config.write(f)
        print(f"🆕 Created default config file at: {os.path.abspath(config_file)}")

    config.read(config_file, encoding="utf-8")
    defaults = config["DEFAULTS"]

    # Expand any %VAR% environment references
    resolved = {k: os.path.expandvars(v) for k, v in defaults.items()}

    return resolved


# =============================================================
#  🎧 MAIN DOWNLOAD FUNCTION
# =============================================================

def download_youtube_audio(url: str, output_folder: str, ffmpeg_path: str):
    """Downloads the best available audio and converts it to MP3."""

    os.makedirs(output_folder, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_folder, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "ffmpeg_location": ffmpeg_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": False,
        "progress_hooks": [
            lambda d: print(f"Status: {d['status']} - {d.get('filename', '')}")
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        print(f"\n✅ Downloaded: {info.get('title', 'unknown')}")
        print(f"📁 Saved to: {output_folder}")

# =============================================================
#  🚀 MAIN ENTRY POINT
# =============================================================

if __name__ == "__main__":
    # Make sure our pseudo environment variable exists
    os.environ["DOWNLOADPATH"] = get_downloads_path()

    config = load_config()

    ffmpeg_path = os.path.abspath(config.get("ffmpeg_path", ""))
    default_url = config.get("default_url", "")
    default_output = os.path.abspath(config.get("default_output_folder", get_downloads_path()))

    print(f"🔧 Using ffmpeg at: {ffmpeg_path}")
    print(f"💾 Default output folder: {default_output}")

    youtube_url = input("\nEnter YouTube URL (press Enter for default): ").strip() or default_url
    output_folder = input("Enter output folder (press Enter for default): ").strip() or default_output

    print(f"\n🎧 Downloading from: {youtube_url}\n")
    download_youtube_audio(youtube_url, output_folder, ffmpeg_path)
