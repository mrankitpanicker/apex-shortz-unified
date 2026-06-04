# run_step2.py
# Runs in 'genv' environment
import os
import sys

# Add the current directory to path so we can import 'src'
sys.path.append(os.getcwd())

from src.config import Config
# We'll use load_text, but we need load_json for the lists
from src.utils import load_text, load_json # Assume load_json is in utils.py
from src.image_gen import ImageGenerator
from src.video_gen import VideoEditor
# We need AudioGenerator here for _chunk_text if the chunks aren't saved!
# But ideally, all lists are saved in Step 1.

def main():
    print("===================================")
    print("🎨 STEP 2: Visuals & Video Render")
    print("===================================")

    # 1. Check & Load Data created by Step 1
    prompt = load_text(Config.FILES["PROMPT"])
    
    # 🔑 NEW: Load the lists of audio paths and text chunks generated in Step 1
    # Assuming these were saved in a JSON file or similar structure.
    # We will assume a file called "CHUNK_DATA" holds a dictionary {audio_paths: [...], text_chunks: [...]}
    chunk_data = load_json(Config.FILES["CHUNK_DATA"]) 
    
    if not prompt or not chunk_data:
        print("❌ Error: Missing inputs (prompt or chunk data). Run Step 1 first.")
        return

    audio_paths = chunk_data.get("audio_paths", [])
    text_chunks = chunk_data.get("text_chunks", [])
    
    if not audio_paths or not text_chunks:
         print("❌ Error: Chunk data is empty. Step 1 failed to generate files.")
         return

    # 2. Image Phase (This remains mostly the same)
    img_engine = ImageGenerator()
    clean_img = img_engine.generate(prompt)

    # 3. Video Phase
    if clean_img:
        video_engine = VideoEditor()
        
        # 🔑 MODIFICATION 1: Pass the list of text chunks AND the list of audio paths 🔑
        ass_file = video_engine.create_subtitles(text_chunks, audio_paths)
        
        # 🔑 MODIFICATION 2: Pass the list of audio paths for merging/rendering 🔑
        video_engine.render(audio_paths)

if __name__ == "__main__":
    main()