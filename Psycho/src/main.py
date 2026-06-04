# main.py

import warnings
import logging
from transformers import logging as hf_logging

# 1. Suppress Torchaudio future change warning
warnings.filterwarnings("ignore", message="In 2.9, this function's implementation will be changed to use torchaudio.load_with_torchcodec", module="torchaudio")

# 2. Suppress Hugging Face Attention Mask warning
hf_logging.set_verbosity_error()
logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR) 

# ... rest of your code execution starts here ...

import os
import warnings
import logging

# --- SILENCE WARNINGS ---
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" 
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("torchaudio").setLevel(logging.ERROR)

from src.config import Config
from src.utils import setup_directories, load_text, get_audio_duration
from src.text_gen import TextGenerator
from src.audio_gen import AudioGenerator
from src.image_gen import ImageGenerator
from src.video_gen import VideoEditor

def main():
    print("===================================")
    print("🎬 AI SHORTS GENERATOR (Modular)")
    print("===================================")
    
    setup_directories()

    # --- 1. Text Phase ---
    text_engine = TextGenerator()
    # Check if we already have text to skip regeneration (Optional)
    if os.path.exists(Config.FILES["RIDDLE"]):
        print("📂 Loading existing riddle...")
        riddle = load_text(Config.FILES["RIDDLE"])
        # We need prompt too
        if os.path.exists(Config.FILES["PROMPT"]):
            prompt = load_text(Config.FILES["PROMPT"])
        else:
            prompt = text_engine.generate_image_prompt(riddle)
    else:
        riddle = text_engine.generate_riddle()
        prompt = text_engine.generate_image_prompt(riddle)

    if not riddle or not prompt: return

    # --- 2. Audio Phase ---
    audio_engine = AudioGenerator()
    audio_engine.generate(riddle)

    # --- 3. Image Phase ---
    img_engine = ImageGenerator()
    img_engine.generate(prompt)

    # --- 4. Video Phase ---
    video_engine = VideoEditor()
    duration = get_audio_duration(Config.FILES["AUDIO_OUT"])
    video_engine.create_subtitles(riddle, duration)
    video_engine.render()

if __name__ == "__main__":
    main()