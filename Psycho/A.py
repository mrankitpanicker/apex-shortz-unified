# A.py
# Runs in 'venv' environment
import os
import sys

# --- ADD THESE LINES TO SUPPRESS WARNINGS ---
import warnings
# Filter warnings from torchaudio/TTS libraries
warnings.filterwarnings("ignore", category=UserWarning, message="In 2.9, this function's implementation will be changed to use torchaudio.load_with_torchcodec")
warnings.filterwarnings("ignore", message="The attention mask is not set and cannot be inferred from input because pad token is same as eos token")
# ---------------------------------------------

# Add the current directory to path so we can import 'src'
sys.path.append(os.getcwd())

from src.utils import save_json, load_text # Ensure save_json is imported
from src.config import Config
from src.utils import setup_directories, save_text # Ensure save_text is available
from src.text_gen import TextGenerator
from src.audio_gen import AudioGenerator

def main():
    print("===================================")
    print("🔊  STEP 1: Text & Audio Generation")
    print("===================================")
    setup_directories() # Ensure output/ is ready

    # 1. Text Phase
    text_engine = TextGenerator()
    
    # Generate Riddle (Full Text)
    riddle = text_engine.generate_riddle()
    if not riddle: return
    
    # Generate Image Prompt
    prompt = text_engine.generate_image_prompt(riddle)
    if not prompt: return
    
    # Save the generated text and prompt for Step 2
    save_text(Config.FILES["RIDDLE"], riddle)
    save_text(Config.FILES["PROMPT"], prompt)
    print(f"✒️ Riddle Saved: {Config.FILES['RIDDLE']}")
    print(f"📒 Prompt Saved: {Config.FILES['PROMPT']}")


    # 2. Audio Phase
    audio_engine = AudioGenerator()
    
    # 🔑 MODIFICATION 1: Capture the lists returned by generate() 🔑
    audio_paths, text_chunks = audio_engine.generate(riddle) 

    if audio_paths:
        # 🔑 MODIFICATION 2: Save the chunk metadata for Step 2 🔑
        chunk_data = {
            "audio_paths": audio_paths,
            "text_chunks": text_chunks
        }
        save_json(Config.FILES["CHUNK_DATA"], chunk_data)
        print(f"📢 Chunk Data Saved for Step 2: {Config.FILES['CHUNK_DATA']}")
        
    else:
        print("❌ Audio generation failed. Cannot proceed.")
        return

if __name__ == "__main__":
    main()