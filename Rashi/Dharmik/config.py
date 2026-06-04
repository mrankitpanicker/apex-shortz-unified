import os
import logging
from pathlib import Path
from datetime import datetime

# --- AGGRESSIVE WARNING/LOGGING SUPPRESSION ---
# Logging setup is placed here as configuration, but should be executed in main.py
# (Keeping it commented out here as per Python best practices, but including 
# the original logic for reference)
# import warnings
# warnings.filterwarnings(
#     "ignore",
#     message="The attention mask is not set and cannot be inferred from input because pad token is same as eos token.",
#     category=UserWarning,
# )
# logging.getLogger().setLevel(logging.ERROR)
# ---------------------------------------------

# --- ENVIRONMENT VARIABLE SETUP ---
# os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "true" 
# (This is better placed in main.py before other imports)
# ----------------------------------

# --- Core Paths ---
rashifal_file = Path(r"D:\tts\Rashi\Dharmik\dataset\dataset.txt")
used_history_file = Path(r"D:\tts\Rashi\Dharmik\dataset\rashifal_used_history.json")
output_dir = Path(r"D:\tts\Rashi\Dharmik\output")
tmp_dir = output_dir / "tmp"
tts_text_dir = tmp_dir / "tts_texts"
speaker_wav = r"D:\tts\Rashi\Dharmik\input\input.wav"
tts_model = "tts_models/multilingual/multi-dataset/xtts_v2"
date_str_format = datetime.now().strftime("%d_%m_%Y")

# **FINAL VIDEO OUTPUT PATH**
FINAL_VIDEO_BASE_DIR = output_dir  

# --- Rashi Video Mapping Configuration (CRITICAL) ---
RASHI_VIDEO_DIR = Path(r"D:\tts\Rashi\Dharmik\input")
RASHI_VIDEO_EXTENSION = ".mp4"

# --- TTS & Audio Config ---
rashis = [
    "मेष",
    "वृषभ",
    "मिथुन",
    "कर्क",
    "सिंह",
    "कन्या",
    "तुला",
    "वृश्चिक",
    "धनु",
    "मकर",
    "कुंभ",
    "मीन",
]

# Map Rashi to its video file number (1-12)
RASHI_TO_VIDEO_MAP = {rashi: i + 1 for i, rashi in enumerate(rashis)}

# --- Subtitle Styling & Sync Config ---
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