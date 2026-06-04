# run_step2.py
# Runs in 'genv' environment
import os
import sys

# Add the current directory to path so we can import 'src'
sys.path.append(os.getcwd())

from src.config import Config
from src.utils import load_text, get_audio_duration
from src.image_gen import ImageGenerator
from src.video_gen import VideoEditor

def main():
    print("===================================")
    print("🎨 STEP 2: Visuals & Video Render")
    print("===================================")

    # Load Data created by Step 1
    prompt = load_text(Config.FILES["PROMPT"])
    riddle = load_text(Config.FILES["RIDDLE"])

    if not prompt or not riddle:
        print("❌ Error: Missing inputs. Run Step 1 first.")
        return

    # 3. Image Phase
    img_engine = ImageGenerator()
    clean_img = img_engine.generate(prompt)

    # 4. Video Phase
    if clean_img:
        video_engine = VideoEditor()
        duration = get_audio_duration(Config.FILES["AUDIO_OUT"])
        
        # Create Subtitles
        ass_file = video_engine.create_subtitles(riddle, duration)
        
        # Render Video
        video_engine.render()

if __name__ == "__main__":
    main()