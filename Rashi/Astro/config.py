import os
from pathlib import Path
from datetime import datetime

# ================================================================
# 1. CORE PATHS & FILES
# ================================================================

# --- Base Paths ---
rashifal_file = Path(r"D:\tts\Rashi\Astro\dataset\dataset.txt")
used_history_file = Path(r"D:\tts\Rashi\Astro\dataset\rashifal_used_history.json")

# --- Directory Paths ---
output_dir = Path(r"D:\tts\Rashi\Astro\output")
tmp_dir = output_dir / "tmp"
tts_text_dir = tmp_dir / "tts_texts"

# **FINAL VIDEO OUTPUT PATH**
FINAL_VIDEO_BASE_DIR = output_dir

# --- TTS & API Config ---
speaker_wav = r"D:\tts\voice\input.wav"
tts_model = "tts_models/multilingual/multi-dataset/xtts_v2"
CLIENT_SECRET_FILE = r"D:\tts\Rashi\Astro\Token\client_secret.json"
TOKEN_FILE = r"D:\tts\Rashi\Astro\Token\token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
MAX_HISTORY_DAYS = 10 # Used in main.py setup logic


# ================================================================
# 2. TIME & MAPPING CONFIGURATION
# ================================================================

date_str_format = datetime.now().strftime("%d_%m_%Y")
today = datetime.now().date()
today_str = datetime.now().strftime("%d %B %Y")

# --- Rashi Video Mapping Configuration (CRITICAL) ---
RASHI_VIDEO_DIR = Path(r"D:\tts\vdeo")
RASHI_VIDEO_EXTENSION = ".mp4"

rashis = [
    "मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", 
    "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन",
]

# Map Rashi to its video file number (1-12)
RASHI_TO_VIDEO_MAP = {rashi: i + 1 for i, rashi in enumerate(rashis)}

# ================================================================
# 3. SUBTITLE STYLING & SYNC CONFIG
# ================================================================

WHISPER_MODEL_NAME = "base"
CHUNK_SIZE_WORDS = 5
VIDEO_W = 1920
VIDEO_H = 1080

SYNC_OFFSET_SECONDS = 1.5
INTER_CHUNK_HOLD_SECONDS = 0.5
INTER_CHUNK_DELAY_SECONDS = 0.5
WORD_DELAY_CS = 3
SUBTITLE_START_DELAY_SECONDS = 4.0

# ASS Styling (Constants)
HIGHLIGHT_COLOR = "&H00FFFF"
BASE_COLOR = "&HFFFFFF"
BORDER_SIZE = 15
SHADOW_SIZE = 6
BLUR_RADIUS = 5
FONT_SIZE = 150