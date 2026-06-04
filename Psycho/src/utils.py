# src/utils.py
import os
import subprocess
import json
from .config import Config


    
def setup_directories():
    """Creates input/output folders if missing."""
    os.makedirs(Config.INPUT_DIR, exist_ok=True)
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)

def load_text(path):
    """Reads text from file."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f: return f.read().strip()
    return None

def save_text(path, content):
    """Saves text to file."""
    with open(path, "w", encoding="utf-8") as f: f.write(content)

def save_json(filepath, data):
    """Saves a dictionary as a JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4) # Saves with nice formatting

def load_json(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def format_ass_time(seconds):
    """Converts seconds to ASS timestamp (H:MM:SS.cs)."""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    cs = int((s - int(s)) * 100)
    return f"{int(h)}:{int(m):02}:{int(s):02}.{cs:02}"

def get_audio_duration(path):
    """Gets exact duration of the audio file using FFmpeg."""
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
        return float(result.stdout.strip())
    except:
        return 10.0 # Fallback