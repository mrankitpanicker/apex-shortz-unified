# src/config.py
import os

class Config:
    # --- PATHS ---
    # Calculates the project root directory relative to this file
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INPUT_DIR = os.path.join(BASE_DIR, "input")
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    
    FILES = {
        "PROMPT": os.path.join(INPUT_DIR, "image_prompt.txt"),
        "RIDDLE": os.path.join(INPUT_DIR, "puzzle_text.txt"),
        "REF_AUDIO": os.path.join(INPUT_DIR, "ref.wav"),
        "AUDIO_OUT": os.path.join(OUTPUT_DIR, "riddle_narration_xtts.wav"),
        "IMAGE_CLEAN": os.path.join(OUTPUT_DIR, "clean_bg.png"),
        "SUBTITLES": os.path.join(OUTPUT_DIR, "riddle.ass"),
        "VIDEO_FINAL": os.path.join(OUTPUT_DIR, "final_short.mp4"),
    }

    # --- API KEYS ---
    # 🛑 PASTE YOUR GEMINI KEY HERE
    GEMINI_API_KEY = "AIzaSyDTJKbSfrrhICwanij43NlgpegjP5Fmt9o"
    GEMINI_MODEL = "gemini-2.5-flash"

    # --- VIDEO STYLE ---
    FONT_NAME = "Noto Sans"
    HEADER_SIZE = 30
    BODY_SIZE = 20
    
    # ASS Colors (&HAABBGGRR)
    COLOR_RED = "&H000000FF"
    COLOR_WHITE = "&H00FFFFFF"

    # --- IMAGE PROMPTS ---
    # Keep this generic so the AI's realistic prompt takes over
    SD_PROMPT_SUFFIX = "8k resolution, photorealistic, cinematic lighting, highly detailed, vertical portrait"
    
    SD_NEGATIVE_PROMPT = "cartoon, anime, drawing, sketch, text, watermark, blurry, low quality"


