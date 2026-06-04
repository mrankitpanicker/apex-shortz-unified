from pathlib import Path
import whisper
import sys
import subprocess 
from datetime import datetime, timedelta

# --- Configuration ---
# NOTE: Replace these paths with your actual file locations.
# The audio and text files should exist for the script to run.
AUDIO_FILE_PATH = Path(r"D:\tts\output/{date_str_format}.wav")
TEXT_FILE_PATH = Path(r"D:\tts\output/{date_str_format}.txt")
# The ASS file path is derived directly from the audio file path
ASS_FILE_PATH = AUDIO_FILE_PATH.with_suffix(".ass")


# Number of words to display per subtitle line (approx. 5-6 requested)
CHUNK_SIZE = 5

# --- Helper Function ---

def format_ass_time(seconds: float) -> str:
    """
    Formats seconds into the exact ASS time format required (H:MM:SS.cc).
    e.g., 65.5 seconds becomes 0:01:05.50
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    # ASS format: H:MM:SS.cc (1-digit hour, 2-digit minute, 5.2f second)
    return f"{h:01d}:{m:02d}:{s:05.2f}"

# --- Main Script ---

try:
    # Initialize total_duration_seconds with a safe default value. 
    # This prevents NameError if execution skips the calculation block.
    total_duration_seconds = 0.0 

    # 1. Load Reference Hindi Text
    print(f"📄 Loading reference text from {TEXT_FILE_PATH}...")
    ref_text = TEXT_FILE_PATH.read_text(encoding="utf-8").strip()
    # Split text into a list of words, removing newlines
    ref_words = ref_text.replace("\n", " ").split()
    print(f"Found {len(ref_words)} words in reference text.")

    # 2. Transcribe with Whisper (Tiny Model)
    print("🎙️ Getting timestamps with Whisper-Tiny. This may take a moment...")
    model = whisper.load_model("tiny")
    result = model.transcribe(str(AUDIO_FILE_PATH), word_timestamps=True, language="hi")

    # 3. Collect Word Timestamps
    timestamps = []
    for seg in result["segments"]:
        # Ensure we only process words that have defined start/end times
        for w in seg.get("words", []):
            start, end, word = w["start"], w["end"], w["word"].strip()
            # Only include words that Whisper successfully timed
            if start is not None and end is not None and word:
                timestamps.append((start, end, word))
    
    print(f"Whisper generated {len(timestamps)} word timestamps.")

    # 4. ASS Header Setup
    # PlayResX/Y define the canvas size for the styling below
    ass = f"""[Script Info]
Title: Hindi Word Sync
ScriptType: v4.00+
Collisions: Normal
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
# PrimaryColour (&H00FFFF) is the highlight color (fill). SecondaryColour (&HFFFFFF) is the base text color.
Style: CenterWord, Noto Sans Devanagari,150,&H00FFFF,&HFFFFFF,&H000000,&H000000,5,0,0,0,100,100,0,0,1,15,6,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # 5. Map Hindi Words to Timestamps and Generate Dialogues
    
    # We use the minimum count of reference words and timed words for safety
    n = min(len(ref_words), len(timestamps))
    print(f"Synchronizing the first {n} words in chunks of {CHUNK_SIZE}...")

    ass_dialogues = []
    
    # Use a pointer to iterate through the words in chunks
    word_pointer = 0
    while word_pointer < n:
        
        # Define chunk boundaries
        chunk_start_index = word_pointer
        chunk_end_index = min(word_pointer + CHUNK_SIZE, n)
        
        # --- 5a. Calculate Chunk Timings ---
        start_time_chunk = timestamps[chunk_start_index][0]
        end_time_chunk = timestamps[chunk_end_index - 1][1]

        # 🕐 Add smooth hold and delay balance
        hold_after_chunk = 1.5  # keep current chunk visible for 350ms
        delay_before_next = 1  # next chunk appears 150ms later

        # Apply hold to end time
        end_time_chunk += hold_after_chunk

        # Delay start time (only after first chunk)
        if chunk_start_index != 0:
            start_time_chunk += delay_before_next

        # Convert to ASS timestamp format
        start_ass = format_ass_time(start_time_chunk)
        end_ass = format_ass_time(end_time_chunk)

        # --- 5b. Build Karaoke-tagged Text ---
        karaoke_text = ""
        
        for i in range(chunk_start_index, chunk_end_index):
            word_start = timestamps[i][0]
            word_end = timestamps[i][1]
            word_text = ref_words[i]

            duration_cs = round((word_end - word_start) * 100 * 2.0)

            # === POP + GLOW EFFECT synced with highlight ===
            karaoke_text += (
                f"{{\\kf{duration_cs}"
        	f"\\1c&H00FFFF&\\blur2\\bord2"  # base highlight
        	# step 1: glow and expand a bit
        	f"\\t(0,100,\\fscx125\\fscy125\\bord5\\blur0\\1c&H00CCFF&)"
        	# step 2: shrink and return to base
    	        f"\\t(100,250,\\fscx100\\fscy100\\bord2\\blur2\\1c&H00FFFF&)}}"
                f"{word_text}"
      	        f"{{\\1c&HFFFFFF&}} "  # reset to white after
            )

        karaoke_text = karaoke_text.strip()

        
        # --- 5c. Create Dialogue Line for the whole chunk ---
        # Dynamic fade duration: adapts fade-out based on line length
        fade_in = 20  # fade-in time (ms)
        fade_out = max(20, int((end_time_chunk - start_time_chunk) * 500 * 0.8))  # fade-out scales with duration

        dialogue_line = (
            f"Dialogue: 0,{start_ass},{end_ass},CenterWord,,0,0,0,,"
            f"{{\\fad({fade_in},{fade_out})\\bord6\\blur6}}{karaoke_text}\n"
        )
        ass_dialogues.append(dialogue_line)
        
        # Move the pointer to the start of the next chunk
        word_pointer = chunk_end_index

    # Append all generated dialogues
    ass += "".join(ass_dialogues)

    # 6. Save Output
    ASS_FILE_PATH.write_text(ass, encoding="utf-8")
    print(f"✅ Chunked, word-level synced ASS saved: {ASS_FILE_PATH.resolve()}")

    # === 7. Execute FFMPEG Command for Video Generation ===

    AUDIO_INPUT_PATH = AUDIO_FILE_PATH.resolve()
    ASS_INPUT_PATH = ASS_FILE_PATH.resolve()
    get_wav_duration = Path(r"D:\tts\output/{date_str_format}.wav")
    duration = get_wav_duration(final_output)
    

    # Define video output path (same name as audio, with .mp4)
    video_base_name = AUDIO_FILE_PATH.stem
    VIDEO_OUTPUT_PATH = AUDIO_FILE_PATH.parent / f"{date_str_format}.mp4"
    VIDEO_OUTPUT_PATH = VIDEO_OUTPUT_PATH.resolve()

    # --- Proper subtitles filter argument ---
    ass_filter_arg = f"ass='{ASS_INPUT_PATH.as_posix()}'"

    # --- Build FFMPEG command ---
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1280x720:d={duration}",
        "-i", audio_input_path,
        # Use the ASS filter for the animated subtitles
        "-vf", subtitles_filter_arg,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p", # Essential for compatibility
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(video_output_path)
    ]


    try:
        print("\n---------------------------------------------------------")
        print("🎬 Running FFMPEG to generate video...")
        print("---------------------------------------------------------")

        # Run FFMPEG safely
        result = subprocess.run(
            ffmpeg_command,
            check=True,
            capture_output=True,
            text=True
        )

        # --- Check output validity ---
        if not VIDEO_OUTPUT_PATH.exists() or VIDEO_OUTPUT_PATH.stat().st_size < 1024:
            raise RuntimeError("Generated video file is missing or too small (likely empty).")

        print("---------------------------------------------------------")
        print(f"✅ FFMPEG video successfully generated:\n{VIDEO_OUTPUT_PATH}")
        print("---------------------------------------------------------")




    except RuntimeError as e:
        print("---------------------------------------------------------")
        print(f"🛑 Generation failed: {e}")
        if 'result' in locals():
            print("🔹 FFMPEG STDOUT:\n", result.stdout)
            print("🔹 FFMPEG STDERR:\n", result.stderr)
        print("---------------------------------------------------------")
        sys.exit(1)

except Exception as e:
    print("---------------------------------------------------------")
    print(f"🛑 Unexpected error: {e}")
    print("---------------------------------------------------------")
    sys.exit(1)

