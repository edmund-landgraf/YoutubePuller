
import os
import subprocess
import datetime
import textwrap
import time
import shutil
import whisper
import whisper.audio
import openai
import types
import numpy as np
import scipy.signal
import json

# ===============================================================
# CONFIGURATION
# ===============================================================

# 🔧 Use the MP3 we created, NOT the Camtasia MP4
AUDIO_SOURCE = r"D:\temp\youtubeaudiooutput\tradeNexus.mp3"

# 🔧 Output transcript directory
OUTPUT_DIR = r"D:\repos\youtubeaudiooutput\camtasia\transcripts"

FFMPEG_PATH = r"D:\ffmpeg\bin\ffmpeg.exe"
MODEL = "large-v3"
LANG = "en"

USE_OPENAI_SUMMARY = False
openai.api_key = os.getenv("OPENAI_API_KEY")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===============================================================
# 1️⃣ Verify FFmpeg
# ===============================================================
print("==============================================================")
print("🔍 SYSTEM PATHS & ENVIRONMENT")
print("==============================================================")
print(f"Python Executable         : {os.sys.executable}")
print(f"Audio Source              : {AUDIO_SOURCE}")
print(f"Output Directory          : {OUTPUT_DIR}")
print(f"FFmpeg Expected Path      : {FFMPEG_PATH}")
print(f"FFmpeg Found (which)      : {shutil.which('ffmpeg')}")
print("--------------------------------------------------------------")

if not os.path.exists(FFMPEG_PATH):
    raise SystemExit(f"❌ FFmpeg not found at {FFMPEG_PATH}")
else:
    print(f"✔️ FFmpeg verified at {FFMPEG_PATH}")

os.environ["PATH"] = f"{os.path.dirname(FFMPEG_PATH)};{os.environ['PATH']}"
whisper.audio.FFMPEG_PATH = FFMPEG_PATH

print("==============================================================\n")


# ===============================================================
# 2️⃣ AUDIO_PATH — Directly use MP3
# ===============================================================
AUDIO_PATH = AUDIO_SOURCE

print(f"🎧 Using MP3 audio source → {AUDIO_PATH}")

if not os.path.exists(AUDIO_PATH):
    raise FileNotFoundError(f"❌ MP3 does not exist: {AUDIO_PATH}")
else:
    print(f"✔️ Found MP3: {AUDIO_PATH}")
    print(f"   Size: {os.path.getsize(AUDIO_PATH) / 1024 / 1024:.2f} MB")


time.sleep(1)

# ===============================================================
# 3️⃣ Patched ffmpeg loader (unchanged)
# ===============================================================
def patched_load_audio(path, sr=16000, *args, **kwargs):
    norm = os.path.abspath(path).replace("\\", "/")
    print(f"🛠️  [Patched] Whisper loading: {norm}")
    cmd = [
        FFMPEG_PATH, "-nostdin", "-threads", "0", "-i", norm,
        "-f", "f32le", "-ac", "1", "-ar", str(sr),
        "-acodec", "pcm_f32le", "-"
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        print("❌ ffmpeg failed.")
        print(e.stderr.decode(errors="ignore")[:400])
        raise
    audio = np.frombuffer(out.stdout, np.float32).flatten()
    print(f"✔️ Loaded {len(audio)} samples at {sr} Hz.")
    return audio

whisper.audio.load_audio = patched_load_audio

# ===============================================================
# 4️⃣ Transcription
# ===============================================================
print("\n==============================================================")
print("🧠 BEGINNING WHISPER TRANSCRIPTION")
print("==============================================================")

try:
    with open(AUDIO_PATH, "rb") as f:
        f.read(32)
    print(f"✔️ File readable: {AUDIO_PATH}")
except Exception as e:
    print(f"❌ Could not read MP3: {e}")
    raise


try:
    model = whisper.load_model(MODEL)
    print(f"✔️ Whisper model '{MODEL}' loaded successfully.")
except Exception as e:
    print(f"❌ Whisper model failed: {e}")
    raise


try:
    result = model.transcribe(AUDIO_PATH, language=LANG, fp16=False)
    print("✔️ Transcription completed successfully.")
except Exception as e:
    print(f"❌ Whisper transcription failed:\n{e}")
    raise


# ===============================================================
# 5️⃣ Save Outputs
# ===============================================================
if result and "text" in result:

    base_name = os.path.splitext(os.path.basename(AUDIO_PATH))[0]
    txt_path  = os.path.join(OUTPUT_DIR, f"{base_name}.txt")
    srt_path  = os.path.join(OUTPUT_DIR, f"{base_name}.srt")
    json_path = os.path.join(OUTPUT_DIR, f"{base_name}.json")

    # --- Save plaintext ---
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])

    # --- Save JSON ---
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # --- Save SRT ---
    if "segments" in result:
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(result["segments"], start=1):
                start = str(datetime.timedelta(seconds=int(seg["start"])))
                end   = str(datetime.timedelta(seconds=int(seg["end"])))
                f.write(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n\n")

    print("--------------------------------------------------------------")
    print(f"💾 Transcript text → {txt_path}")
    print(f"💾 Transcript SRT  → {srt_path}")
    print(f"💾 Transcript JSON → {json_path}")
    print("--------------------------------------------------------------")

else:
    print("⚠️ Whisper returned no text.")

print("✅ Transcription workflow complete.")
