# step1.py
# Runs in 'venv' environment
import os
import sys

# Add the current directory to path so we can import 'src'
sys.path.append(os.getcwd())

from src.config import Config
from src.utils import setup_directories
from src.text_gen import TextGenerator
from src.audio_gen import AudioGenerator

def main():
    print("===================================")
    print("🔊  STEP 1: Text & Audio Generation")
    print("===================================")
    setup_directories()

    # 1. Text Phase
    text_engine = TextGenerator()
    riddle = text_engine.generate_riddle()
    if not riddle: return
    
    prompt = text_engine.generate_image_prompt(riddle)
    if not prompt: return

    # 2. Audio Phase
    audio_engine = AudioGenerator()
    audio_engine.generate(riddle)

if __name__ == "__main__":
    main()