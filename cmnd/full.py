#!/usr/bin/env python
import random
import re
from pathlib import Path
import json
from datetime import datetime, timedelta
import subprocess
import whisper
import sys
import shlex
import time
import wave 
import contextlib 
import os
import argparse 

# === Allow XTTS-related classes to be unpickled safely (PyTorch 2.6+) ===
try:
    import torch
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
    from TTS.config.shared_configs import BaseDatasetConfig
    from TTS.api import TTS
    
    # Safely adding globals for PyTorch unpickling
    torch.serialization.add_safe_globals(
        [
            XttsConfig,
            XttsAudioConfig,
            XttsArgs,
            BaseDatasetConfig,
        ]
    )
except ImportError:
    pass 
# ================================================================

# ================================================================
#                             CONFIGURATION
# ================================================================

# --- Core Paths ---
rashifal_file = Path(r"C:\Users\ankyp\Desktop\dataset.txt")
used_history_file = Path(r"C:\Users\ankyp\Desktop\rashifal_used_history.json")
output_dir = Path(r"D:\tts\output")
tmp_dir = output_dir / "tmp"
tts_text_dir = tmp_dir / "tts_texts"
speaker_wav = r"D:\tts\input.wav"
tts_model = "tts_models/multilingual/multi-dataset/xtts_v2"
date_str_format = datetime.now().strftime("%d_%m_%Y")

# **FINAL VIDEO OUTPUT PATH**
FINAL_VIDEO_OUTPUT_DIR = output_dir / "rashi" 

# --- Rashi Video Mapping Configuration (CRITICAL) ---
# **SET THIS PATH TO YOUR VIDEO FOLDER (D:\tts\vdeo)**
RASHI_VIDEO_DIR = Path(r"D:\tts\vdeo") 
RASHI_VIDEO_EXTENSION = ".mp4" 

# --- TTS & Audio Config ---
rashis = [
    "मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", 
    "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन",
]

# Map Rashi to its video file number (1-12)
RASHI_TO_VIDEO_MAP = {rashi: i + 1 for i, rashi in enumerate(rashis)}

# --- Subtitle Styling & Sync Config ---
WHISPER_MODEL_NAME = "base"
CHUNK_SIZE_WORDS = 5 
VIDEO_W = 1920 
VIDEO_H = 1080

# 1. GLOBAL SYNC: Adjust this value to fix Whisper's timing mismatch with XTTS.
SYNC_OFFSET_SECONDS = 1.5 

# 2. CHUNK HOLD: How long the final line stays visible *after* the last word highlight ends.
INTER_CHUNK_HOLD_SECONDS = 0.5 

# 3. INTER-CHUNK DELAY: Pause added BEFORE the next line appears (after the hold).
INTER_CHUNK_DELAY_SECONDS = 0.5

# 4. WORD DELAY: Time delay (in centiseconds) before the next word's highlight begins.
WORD_DELAY_CS = 3 

# 5. START AUDIO DELAY (FROM VIDEO START): Start audio and subtitle 4 seconds into the video.
SUBTITLE_START_DELAY_SECONDS = 4.0 

# ASS Styling (Constants)
HIGHLIGHT_COLOR = "&H00FFFF"  # Yellow (Fill)
BASE_COLOR = "&HFFFFFF"      # White (Secondary)
BORDER_SIZE = 15            
SHADOW_SIZE = 6
BLUR_RADIUS = 5
FONT_SIZE = 150

# ================================================================
#                             UTILITY FUNCTIONS
# ================================================================

num_to_hindi = {
    5: "पाँच प्रतिशत", 10: "दस प्रतिशत", 15: "पंद्रह प्रतिशत", 20: "बीस प्रतिशत",
    25: "पच्चीस प्रतिशत", 30: "तीस प्रतिशत", 35: "पैंतीस प्रतिशत", 40: "चालीस प्रतिशत",
    45: "पैंतालीस प्रतिशत", 50: "पचास प्रतिशत", 55: "पचपन प्रतिशत", 60: "साठ प्रतिशत",
    65: "पैंसठ प्रतिशत", 70: "सत्तर प्रतिशत", 75: "पचहत्तर प्रतिशत", 80: "अस्सी प्रतिशत",
    85: "पचासी प्रतिशत", 90: "नब्बे प्रतिशत", 95: "पंचानबे प्रतिशत", 100: "सौ प्रतिशत",
}

def convert_number_to_hindi(match):
    """Converts a matched percentage number to its Hindi word equivalent."""
    num = int(match.group(1))
    return num_to_hindi.get(num, match.group(0))

def fix_hindi_pronunciation(txt: str) -> str:
    """Fixes common pronunciation issues for better TTS quality."""
    return txt.replace("प्रतिशत", "प्रतिशथ")

def split_text_safe(text, max_len=200):
    """Splits text into chunks by sentence boundary, ensuring chunks are under max_len."""
    sentences = re.split(r"(?<=[।.!?])\s*", text)
    chunks = []
    current = ""
    for s in sentences:
        s = s.strip()
        if not s: continue
        if len(current) + len(s) + 1 <= max_len:
            current += (" " if current else "") + s
        else:
            if current: chunks.append(current.strip())
            current = s
    if current: chunks.append(current.strip())
    unique_chunks = []
    for c in chunks:
        if c not in unique_chunks: unique_chunks.append(c)
    return unique_chunks

def get_wav_duration(wav_file: Path) -> float:
    """Calculates the duration of a WAV file in seconds."""
    try:
        with contextlib.closing(wave.open(str(wav_file), "rb")) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        # Fallback to ffprobe
        res = subprocess.run(
            ["ffprobe", "-i", str(wav_file), "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"],
            capture_output=True, text=True,
        )
        try:
            return float(res.stdout.strip())
        except (ValueError, IndexError):
            print(f"Warning: Could not get duration for {wav_file} using ffprobe.")
            return 0.0

def run_ffmpeg_command(cmd, desc):
    """Helper function to run FFmpeg with diagnostics."""
    print(f"\n⚙️ Running FFmpeg command for: {desc}")
    print(f"Command: {' '.join(shlex.quote(c) for c in cmd)}")
    try:
        subprocess.run(
            cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
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
        print("\n🚨 ERROR: FFmpeg executable not found. Make sure it is installed and added to your system PATH.")
        raise FileNotFoundError("FFmpeg executable not found.")

def format_ass_time(seconds: float) -> str:
    """Formats time in ASS format (H:MM:SS.cc)."""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:01d}:{m:02d}:{s:05.2f}"

# ================================================================
#                       VIDEO SEGMENT GENERATION CORE
# ================================================================

def generate_video_segment(audio_path: Path, text_path: Path, output_dir: Path, rashi: str) -> Path | None:
    """
    Generates a subtitled video for a single Rashi using its dedicated, numbered video file.
    """
    
    # Locate the Rashi's video file using the 1-12 index.
    video_number = RASHI_TO_VIDEO_MAP.get(rashi)
    if not video_number:
        print(f"🚨 ERROR: Rashi '{rashi}' not found in video map. Skipping.")
        return None
        
    rashi_video_input = RASHI_VIDEO_DIR / f"{video_number}{RASHI_VIDEO_EXTENSION}"

    if not rashi_video_input.exists():
        print(f"🚨 ERROR: Input video for {rashi} not found at {rashi_video_input.resolve()}. Skipping.")
        return None
        
    # --- Output Path ---
    FINAL_VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    segment_output_path = FINAL_VIDEO_OUTPUT_DIR / f"{rashi}_{date_str_format}.mp4"
    ass_path = audio_path.with_suffix(".ass")
    # -------------------
    
    # 1. Get Rashi Audio Duration and calculate final video duration
    rashi_audio_duration = get_wav_duration(audio_path)
    # The total duration of the output video is the audio duration plus the 4-second delay.
    final_output_duration = rashi_audio_duration + SUBTITLE_START_DELAY_SECONDS 
    
    # 2. Transcribe with Whisper 
    print(f"\n📄 Loading reference text from {text_path.name}...")
    ref_text = text_path.read_text(encoding="utf-8").strip()
    ref_words = ref_text.replace("\n", " ").split()
    
    print(f"🎙️ Getting word timestamps for {rashi}...")
    try:
        model = whisper.load_model(WHISPER_MODEL_NAME)
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        return None

    result = model.transcribe(str(audio_path), word_timestamps=True, language="hi")

    timestamps = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            start, end, word = w["start"], w["end"], w["word"].strip()
            # Apply the global sync offset (1.5s) to the Rashi audio's timestamps
            start = start + SYNC_OFFSET_SECONDS
            end = end + SYNC_OFFSET_SECONDS
            
            if start is not None and end is not None and word and start >= 0:
                timestamps.append((start, end, word))
    
    n = min(len(ref_words), len(timestamps))
    
    # --- 3. ASS Header Setup (Remains the same) ---
    ass = f"""[Script Info]
Title: Hindi Word Sync - {rashi}
ScriptType: v4.00+
Collisions: Normal
PlayResX: {VIDEO_W}
PlayResY: {VIDEO_H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: CenterWord, Noto Sans Devanagari,{FONT_SIZE},{HIGHLIGHT_COLOR},{BASE_COLOR},&H000000,&H000000,5,0,0,0,100,100,0,0,1,{BORDER_SIZE},{SHADOW_SIZE},5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # 4. Generate Dialogues (ASS events) - Apply SUBTITLE_START_DELAY_SECONDS
    ass_dialogues = []
    word_pointer = 0
    while word_pointer < n:
        chunk_start_index = word_pointer
        # Enforce 5 words maximum chunk size explicitly
        chunk_end_index = min(word_pointer + CHUNK_SIZE_WORDS, n)
        
        # --- Calculate Chunk Timings ---
        base_start_time = timestamps[chunk_start_index][0]
        end_time_last_word = timestamps[chunk_end_index - 1][1]
        
        # Start Time: Apply the GLOBAL START DELAY to all subtitle times
        start_time_chunk = base_start_time + SUBTITLE_START_DELAY_SECONDS 

        # Subtitle Overlap Fix: Ensure a small delay for the text to appear after the previous one disappears
        if chunk_start_index != 0:
            start_time_chunk += INTER_CHUNK_DELAY_SECONDS

        # End Time: Last word end + 4s delay + Hold time (This is the point where the line should *disappear*)
        end_time_chunk = end_time_last_word + SUBTITLE_START_DELAY_SECONDS + INTER_CHUNK_HOLD_SECONDS 
        
        start_ass = format_ass_time(start_time_chunk)
        end_ass = format_ass_time(end_time_chunk)

        # --- Build Karaoke-tagged Text (Timing logic is already precise) ---
        karaoke_text = ""
        
        for i in range(chunk_start_index, chunk_end_index):
            word_start = timestamps[i][0]
            word_end = timestamps[i][1]
            word_text = ref_words[i] if i < len(ref_words) else timestamps[i][2]
            
            duration_cs = round((word_end - word_start) * 100)
            
            # Calculate word start time relative to the dialogue line start (start_time_chunk)
            if i == chunk_start_index:
                 # Delay from Dialogue Start (start_time_chunk) to the word's actual start (word_start + delay)
                 delay_from_start_s = (word_start + SUBTITLE_START_DELAY_SECONDS) - start_time_chunk
                 delay_from_start_cs = max(0, round(delay_from_start_s * 100))
                 karaoke_text += f"{{\\k{delay_from_start_cs}}}"
            else:
                 karaoke_text += f"{{\\k{WORD_DELAY_CS}}}" 

            karaoke_text += (
                f"{{\\kf{duration_cs}"
                f"\\1c{HIGHLIGHT_COLOR}}}" 
                f"{word_text}"
                f"{{\\1c{BASE_COLOR}}} "
            )

        karaoke_text = karaoke_text.strip()
        
        # --- Create Dialogue Line ---
        fade_in = 20
        # Calculate fade out time relative to the line's visual duration
        fade_out = max(20, int((end_time_chunk - start_time_chunk) * 500 * 0.8))

        dialogue_line = (
            f"Dialogue: 0,{start_ass},{end_ass},CenterWord,,0,0,0,,"
            f"{{\\fad({fade_in},{fade_out})\\bord{BORDER_SIZE}\\blur{BLUR_RADIUS}}}{karaoke_text}\n"
        )
        ass_dialogues.append(dialogue_line)
        word_pointer = chunk_end_index

    ass += "".join(ass_dialogues)
    ass_path.write_text(ass, encoding="utf-8")
    print(f"✅ ASS script saved for {rashi}.")

    # 5. Execute FFMPEG Command for Subtitling and Trimming
    
    ass_filter_path_escaped = str(ass_path.resolve()).replace('\\', '\\\\').replace(':', '\\:')
    ass_filter_arg = f"ass='{ass_filter_path_escaped}'" 

    # --- FFmpeg Command for Subtitling, Start Offset, and Trimming ---
    cmd = [
        "ffmpeg", "-y",
        
        # Input 1 (Video)
        "-i", str(rashi_video_input.resolve()),
        
        # Input 2 (Audio)
        "-i", str(audio_path.resolve()), 
        
        # Video filter
        "-vf", ass_filter_arg,
        
        # Audio filter: Add 4000ms (4 seconds) of silence at the start
        "-filter_complex", f"[1:a]adelay={int(SUBTITLE_START_DELAY_SECONDS * 1000)}|{int(SUBTITLE_START_DELAY_SECONDS * 1000)}[a]",

        # Map streams
        "-map", "0:v:0", 
        "-map", "[a]",   
        
        # Duration control
        "-t", f"{final_output_duration:.3f}", 
        
        # Encoding settings
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        
        str(segment_output_path),
    ]

    try:
        run_ffmpeg_command(cmd, f"Video Generation: {rashi}")
        return segment_output_path
    except Exception as e:
        print(f"🛑 Video Generation Failed for {rashi}: {e}")
        return None


# ================================================================
#                       TTS AND GENERATION CORE
# ================================================================

def main(test_mode=False):
    # --- Read & clean dataset ---
    try:
        full_text = rashifal_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Dataset file not found at {rashifal_file}. Please check the path and permissions.")
        sys.exit(1)

    clean_text_data = re.sub(r"\[.*?\]", "", full_text).strip()
    blocks = re.split(r"(?=\b(?:" + "|".join(rashis) + r")\s*राशि)", clean_text_data)
    cleaned = []
    seen = set()
    for b in blocks:
        for r in rashis:
            if r in b and r not in seen:
                b = re.sub(r"अगर आप मुझसे जुड़.*", "", b, flags=re.DOTALL)
                b = re.sub(r"\s+", " ", b).strip()
                cleaned.append(b)
                seen.add(r)
                break
    
    if not cleaned:
        print("Error: No horoscope data found after cleaning the dataset file.")
        sys.exit(1)

    # --- History and Data Setup ---
    HISTORY_PATH = used_history_file
    MAX_HISTORY_DAYS = 10
    today = datetime.now().date()
    
    if HISTORY_PATH.exists():
        try:
            used_history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("⚠️ History file corrupted — resetting.")
            used_history = {}
    else:
        used_history = {}

    for rashi, entries in list(used_history.items()):
        if not isinstance(entries, list):
            used_history[rashi] = []
            continue
        used_history[rashi] = [
            e
            for e in entries
            if isinstance(e, dict) and "date" in e
            and datetime.strptime(e["date"], "%Y-%m-%d").date() >= today - timedelta(days=MAX_HISTORY_DAYS)
        ]

    daily_rashifal = {}
    for rashi, script in zip(rashis, cleaned):
        chosen = re.sub(r"\b(5|10|15|20|25|30|35|40|45|50|55|60|65|70|75|80|85|90|95|100)%", convert_number_to_hindi, script,)
        chosen = fix_hindi_pronunciation(chosen)
        
        # Random text replacement logic
        chosen = re.sub(r"आज", lambda _: random.choice([
            "स्वास्थ्य आपका कुल मिलाजुलाकर ठीक बना रहेगा।", "धन लाभ के योग बन रहे हैं।", "परिवार में मंगल कार्य होंगे।",
            "किसी निर्धन व्यक्ति को अगर धन का दान कर दें तो दिन बेहतर होगा।", 
            "शुभ रंग होगा आपके लिए आसमानी और भाग्य का मीटर आपको नंबर दे रहा है।", 
            "75% उत्तम भाग्य आपके साथ बना हुआ है।", "धन की स्थिति अच्छी रहेगी।", 
            "कारोबार में आपको लाभ होगा।", "स्वास्थ्य उत्तम हो जाएगा।"
            ]), chosen)
            
        daily_rashifal[rashi] = chosen
        used_history.setdefault(rashi, []).append({"text": chosen, "date": str(today)})

    HISTORY_PATH.write_text(json.dumps(used_history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"🧠 Updated {len(used_history)} rashis in history. Generating TTS now.")

    # --- Directory setup ---
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tts_text_dir.mkdir(exist_ok=True)

    # Initialize TTS model
    print(f"Loading TTS model: {tts_model}...")
    try:
        tts = TTS(tts_model)
    except Exception as e:
        print(f"Error loading TTS model: {e}")
        sys.exit(1)

    rashi_list = [rashis[0]] if test_mode else rashis 
    generated_count = 0
    
    # List to store paths of successfully generated videos for final merge
    # --- FIX APPLIED HERE ---
    all_rashi_video_paths = [] 
    # -------------------------

    for rashi in rashi_list:
        if rashi not in daily_rashifal: 
            print(f"⚠️ Skipping {rashi}: Not in daily data.")
            continue

        # Check for Rashi video file presence before doing TTS
        video_number = RASHI_TO_VIDEO_MAP.get(rashi)
        rashi_video_input = RASHI_VIDEO_DIR / f"{video_number}{RASHI_VIDEO_EXTENSION}"
        if not video_number or not rashi_video_input.exists():
             print(f"🚨 ERROR: Input video for {rashi} (expected {video_number}{RASHI_VIDEO_EXTENSION}) not found. Skipping.")
             continue


        text = daily_rashifal[rashi]
        chunks = split_text_safe(text, max_len=200)

        if test_mode and rashi == rashi_list[0]:
            chunks = [chunks[0]] 
            print("⚡ Test mode: generating only the first chunk of the first rashi.")

        temp_files = []

        # --- Generate Chunks Audio & Text ---
        for i, chunk in enumerate(chunks):
            out_file = tmp_dir / f"{rashi}_{i}.wav"
            txt_file = tts_text_dir / f"{rashi}_{i}.txt"
            txt_file.write_text(chunk, encoding="utf-8")

            print(f"🎼 Generating TTS for {rashi}, chunk {i+1}/{len(chunks)}...")

            tts.tts_to_file(
                text=chunk, speaker_wav=speaker_wav, language="hi", file_path=str(out_file),
            )
            if not out_file.exists() or out_file.stat().st_size == 0:
                print(f"Warning: TTS output missing or zero-length for {rashi}_{i}. Skipping chunk.")
                continue
            temp_files.append(str(out_file))

        # --- Merge chunks per rashi to get the final Rashi AUDIO file ---
        if not temp_files: continue
        rashi_concat_file = tmp_dir / f"{rashi}_concat.txt"
        with open(rashi_concat_file, "w", encoding="utf-8") as f:
            for wav in temp_files:
                f.write(f"file '{Path(wav).as_posix()}'\n")

        # The final audio file for this Rashi
        rashi_audio_path = tmp_dir / f"{rashi}.wav" 
        rashi_text_path = tts_text_dir / f"{rashi}.txt"
        rashi_text_path.write_text("\n\n".join(chunks), encoding="utf-8") # Save combined text

        # FFmpeg command to concatenate audio chunks
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(rashi_concat_file), 
            "-af", "volume=4.0,dynaudnorm=f=75", "-c:a", "pcm_s16le", str(rashi_audio_path),
        ]
        try:
            run_ffmpeg_command(cmd, f"Rashi Chunk Merge: {rashi}")
        except Exception:
            print(f"❌ Failed to merge chunks for {rashi}. Skipping this rashi.")
            if test_mode: sys.exit(1)
            continue
        
        # --- GENERATE FINAL VIDEO FOR THIS RASHI ---
        video_segment_path = generate_video_segment(
            rashi_audio_path, rashi_text_path, output_dir, rashi
        )
        if video_segment_path and video_segment_path.exists():
            print(f"🎉 FINAL VIDEO GENERATED: {video_segment_path.name}\n")
            generated_count += 1
            all_rashi_video_paths.append(video_segment_path) # <<< COLLECT PATH
        
        # Clean up temporary files for this Rashi
        rashi_concat_file.unlink(missing_ok=True)
        for f in temp_files: Path(f).unlink(missing_ok=True)
        rashi_audio_path.unlink(missing_ok=True)
        rashi_text_path.unlink(missing_ok=True)
        
        if test_mode: break
    
    # ================================================================
    #                        FINAL MERGE STEP
    # ================================================================
    if len(all_rashi_video_paths) > 1:
        print("\n🎬 Starting final merge of all Rashi videos...")
        
        # 1. Create the concatenation list file
        concat_list_file = tmp_dir / "final_concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for path in all_rashi_video_paths:
                f.write(f"file '{path.as_posix()}'\n")
        
        final_output_video = FINAL_VIDEO_OUTPUT_DIR / f"Final_Rashifal_{date_str_format}.mp4"
        
        # 2. FFmpeg Concatenation Command (using the concat demuxer)
        merge_cmd = [
            "ffmpeg", "-y", 
            "-f", "concat", 
            "-safe", "0", 
            "-i", str(concat_list_file),
            "-c", "copy", # Fast and lossless merging since all videos are already encoded
            str(final_output_video)
        ]

        try:
            run_ffmpeg_command(merge_cmd, "FINAL VIDEO MERGE")
            print(f"\n✨ **COMPLETE VIDEO GENERATED:** {final_output_video.resolve()}")
            # Optionally clean up the concat list
            concat_list_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"🛑 FINAL VIDEO MERGE FAILED: {e}")

    elif len(all_rashi_video_paths) == 1:
         print("\n⚠️ Only one Rashi video was generated. Skipping merge.")
    else:
        print("\n❌ No Rashi videos were successfully generated. Nothing to merge.")

    print(f"\n✨ Script finished. Generated {generated_count} individual Rashi videos in {FINAL_VIDEO_OUTPUT_DIR.resolve()}.")


# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate daily rashifal video from TTS and subtitles.")
    parser.add_argument("--test", action="store_true", help="Run in test mode (only processes the first chunk of the first rashi and breaks).")
    args = parser.parse_args()
    main(test_mode=args.test)