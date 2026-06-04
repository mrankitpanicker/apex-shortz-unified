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
       # 🔑 STEP 1 to STEP 2 BRIDGE 🔑
        "CHUNK_DATA": os.path.join(OUTPUT_DIR, "chunk_data.json"), 
        
        # 🔑 FIX: TEMPORARY AUDIO MERGE FILE 🔑
        "AUDIO_MERGED": os.path.join(OUTPUT_DIR, "merged_audio.wav"),
        
        # Final Output
        "VIDEO_FINAL": os.path.join(OUTPUT_DIR, "final_short.mp4"),
    }

    # --- API KEYS ---
    # 🛑 PASTE YOUR GEMINI KEY HERE
    GEMINI_API_KEY = "AIzaSyDTJKbSfrrhICwanij43NlgpegjP5Fmt9o"
    GEMINI_MODEL = "gemini-2.5-flash"

    # --- VIDEO STYLE ---
    FONT_NAME = "Noto Sans Devanagari"   # supports Hindi + Latin both

    # --- VIDEO STYLE ---
    FONT_NAME = "Noto Sans Devanagari"

    # This is a VERTICAL (portrait) video — typical shorts/reels resolution
    PLAY_RES_X = 1080
    PLAY_RES_Y = 1920

    # Sizes tuned for 1080x1920 portrait
    HEADER_SIZE = 90    # title at top
    BODY_SIZE   = 72    # body facts — bold and centered

    # ASS Colors (&H00BBGGRR)
    COLOR_RED    = "&H000000FF"
    COLOR_YELLOW = "&H0000FFFF"
    COLOR_WHITE  = "&H00FFFFFF"

    # --- IMAGE PROMPTS ---
    # Keep this generic so the AI's realistic prompt takes over
    # SD_PROMPT_SUFFIX: Now emphasizes artistic style and emotional depth
    SD_PROMPT_SUFFIX = "Unreal Engine 5, Octane Render, Dramatic volumetric lighting, Hyper-realistic, cinematic vertical portrait, macro shot, deep focus, emotional atmosphere"
    
    # SD_NEGATIVE_PROMPT: Strengthened to eliminate all non-photorealistic elements and low-quality artifacts
    SD_NEGATIVE_PROMPT = "cartoon, anime, drawing, sketch, text, signature, watermark, blurry, deformed, low quality, cropped, bright white light, cheerful, childish"


