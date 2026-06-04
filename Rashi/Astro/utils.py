import re
import subprocess
import shlex
import wave
import contextlib
from pathlib import Path

# ================================================================
# 1. HINDI TEXT CONVERSION UTILITIES
# ================================================================

num_to_hindi = {
    5: "पाँच प्रतिशत", 10: "दस प्रतिशत", 15: "पंद्रह प्रतिशत", 
    20: "बीस प्रतिशत", 25: "पच्चीस प्रतिशत", 30: "तीस प्रतिशत", 
    35: "पैंतीस प्रतिशत", 40: "चालीस प्रतिशत", 45: "पैंतालीस प्रतिशत", 
    50: "पचास प्रतिशत", 55: "पचपन प्रतिशत", 60: "साठ प्रतिशत", 
    65: "पैंसठ प्रतिशत", 70: "सत्तर प्रतिशत", 75: "पचहत्तर प्रतिशत", 
    80: "अस्सी प्रतिशत", 85: "पचासी प्रतिशत", 90: "नब्बे प्रतिशत", 
    95: "पंचानबे प्रतिशत", 100: "सौ प्रतिशत",
}


def convert_number_to_hindi(match):
    """Converts a matched percentage number to its Hindi word equivalent."""
    num = int(match.group(1))
    return num_to_hindi.get(num, match.group(0))


def fix_hindi_pronunciation(txt: str) -> str:
    """Fixes common pronunciation issues for better TTS quality."""
    # Ensure proper spacing after period for TTS pause
    txt = txt.replace("।", "। ")
    # Fix the common mispronunciation of "pratishat"
    txt = txt.replace("प्रतिशत", "प्रतिशथ")
    # Clean up any excess spaces created by replacement
    return txt.replace("।  ", "। ")


def split_text_safe(text, max_len=200):
    """Splits text into chunks by sentence boundary, ensuring chunks are under max_len."""
    sentences = re.split(r"(?<=[।.!?])\s*", text)
    chunks = []
    current = ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(current) + len(s) + 1 <= max_len:
            current += (" " if current else "") + s
        else:
            if current:
                chunks.append(current.strip())
            current = s
    if current:
        chunks.append(current.strip())

    unique_chunks = []
    for c in chunks:
        if c not in unique_chunks:
            # Add an explicit comma to the end of a non-terminal chunk for a slight pause
            if (
                not c.endswith(("।", "?", "!", ".", ","))
                and len(unique_chunks) < len(chunks) - 1
            ):
                unique_chunks.append(c + ",")
            else:
                unique_chunks.append(c)
    return unique_chunks

# ================================================================
# 2. FILE/TIME UTILITIES
# ================================================================

def get_wav_duration(wav_file: Path) -> float:
    """Calculates the duration of a WAV file in seconds (using wave or ffprobe)."""
    try:
        with contextlib.closing(wave.open(str(wav_file), "rb")) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        # Fallback to ffprobe
        res = subprocess.run(
            [
                "ffprobe", "-i", str(wav_file), 
                "-show_entries", "format=duration", 
                "-v", "quiet", "-of", "csv=p=0",
            ],
            capture_output=True,
            text=True,
        )
        try:
            return float(res.stdout.strip())
        except (ValueError, IndexError):
            print(f"Warning: Could not get duration for {wav_file} using ffprobe.")
            return 0.0


def format_ass_time(seconds: float) -> str:
    """Formats time in ASS format (H:MM:SS.cc)."""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:01d}:{m:02d}:{s:05.2f}"


def run_ffmpeg_command(cmd, desc):
    """Helper function to run FFmpeg with diagnostics."""
    print(f"\n⚙️ Running FFmpeg command for: {desc}")
    print(f"Command: {' '.join(shlex.quote(c) for c in cmd)}")
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print(f"✅ FFmpeg success: {desc}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n🚨 FFMPEG ERROR DETAILS for {desc} (Return Code {e.returncode}):")
        print("---------------------------------------------------------")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        print("---------------------------------------------------------")
        raise RuntimeError(f"FFmpeg failed during {desc}. See details above.")
    except FileNotFoundError:
        print(
            "\n🚨 ERROR: FFmpeg executable not found. Make sure it is installed and added to your system PATH."
        )
        raise FileNotFoundError("FFmpeg executable not found.")