# ================================================================
#           --- 5. VIDEO SEGMENT GENERATION CORE ---
# ================================================================

import warnings

warnings.filterwarnings(
    "ignore",
    message="Failed to launch Triton kernels, likely due to missing CUDA toolkit; falling back to",
    category=UserWarning,
)


import subprocess
from pathlib import Path
import whisper
import utils
import config # Import configuration constants

import warnings

warnings.filterwarnings(
    "ignore",
    message="Failed to launch Triton kernels, likely due to missing CUDA toolkit; falling back to",
    category=UserWarning,
)


def generate_video_segment(
    audio_path: Path, text_path: Path, output_dir: Path, rashi: str
) -> Path | None:
    """
    Generates a subtitled video for a single Rashi using its dedicated, numbered video file.
    """

    # Locate the Rashi's video file using the 1-12 index.
    video_number = config.RASHI_TO_VIDEO_MAP.get(rashi)
    if not video_number:
        print(f"🚨 ERROR: Rashi '{rashi}' not found in video map. Skipping.")
        return None

    rashi_video_input = config.RASHI_VIDEO_DIR / f"{video_number}{config.RASHI_VIDEO_EXTENSION}"

    if not rashi_video_input.exists():
        print(
            f"🚨 ERROR: Input video for {rashi} not found at {rashi_video_input.resolve()}. Skipping."
        )
        return None

    # --- Output Path ---
    config.FINAL_VIDEO_BASE_DIR.mkdir(parents=True, exist_ok=True)
    segment_output_path = config.FINAL_VIDEO_BASE_DIR / f"{rashi}_{config.date_str_format}.mp4"
    ass_path = audio_path.with_suffix(".ass")
    # -------------------

    # 1. Get Rashi Audio Duration and calculate final video duration
    rashi_audio_duration = utils.get_wav_duration(audio_path)
    # The total duration of the output video is the audio duration plus the 4-second delay.
    final_output_duration = rashi_audio_duration + config.SUBTITLE_START_DELAY_SECONDS

    # 2. Transcribe with Whisper
    print(f"\n📄 Loading reference text from {text_path.name}...")
    ref_text = text_path.read_text(encoding="utf-8").strip()
    ref_words = ref_text.replace("\n", " ").split()

    print(f"🎙️ Getting word timestamps for {rashi} using {config.WHISPER_MODEL_NAME}...")
    try:
        model = whisper.load_model(config.WHISPER_MODEL_NAME)
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        return None

    result = model.transcribe(str(audio_path), word_timestamps=True, language="hi")

    timestamps = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            start, end, word = w["start"], w["end"], w["word"].strip()
            # Apply the global sync offset (1.5s) to the Rashi audio's timestamps
            start = start + config.SYNC_OFFSET_SECONDS
            end = end + config.SYNC_OFFSET_SECONDS

            if start is not None and end is not None and word and start >= 0:
                timestamps.append((start, end, word))

    n = min(len(ref_words), len(timestamps))

    # --- 3. ASS Header Setup ---
    ass = f"""[Script Info]
Title: Hindi Word Sync - {rashi}
ScriptType: v4.00+
Collisions: Normal
PlayResX: {config.VIDEO_W}
PlayResY: {config.VIDEO_H}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: CenterWord, Noto Sans Devanagari,{config.FONT_SIZE},{config.HIGHLIGHT_COLOR},{config.BASE_COLOR},&H000000,&H000000,5,0,0,0,100,100,0,0,1,{config.BORDER_SIZE},{config.SHADOW_SIZE},5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # 4. Generate Dialogues (ASS events) - Apply SUBTITLE_START_DELAY_SECONDS
    ass_dialogues = []
    word_pointer = 0
    while word_pointer < n:
        chunk_start_index = word_pointer
        # Enforce 5 words maximum chunk size explicitly
        chunk_end_index = min(word_pointer + config.CHUNK_SIZE_WORDS, n)

        # --- Calculate Chunk Timings ---
        base_start_time = timestamps[chunk_start_index][0]
        end_time_last_word = timestamps[chunk_end_index - 1][1]

        # Start Time: Apply the GLOBAL START DELAY to all subtitle times
        start_time_chunk = base_start_time + config.SUBTITLE_START_DELAY_SECONDS

        # Subtitle Overlap Fix: Ensure a small delay for the text to appear after the previous one disappears
        if chunk_start_index != 0:
            start_time_chunk += config.INTER_CHUNK_DELAY_SECONDS

        # End Time: Last word end + delay + Hold time
        end_time_chunk = (
            end_time_last_word + config.SUBTITLE_START_DELAY_SECONDS + config.INTER_CHUNK_HOLD_SECONDS
        )

        start_ass = utils.format_ass_time(start_time_chunk)
        end_ass = utils.format_ass_time(end_time_chunk)

        # --- Build Karaoke-tagged Text ---
        karaoke_text = ""

        for i in range(chunk_start_index, chunk_end_index):
            word_start = timestamps[i][0]
            word_end = timestamps[i][1]
            word_text = ref_words[i] if i < len(ref_words) else timestamps[i][2]

            duration_cs = round((word_end - word_start) * 100)

            # Calculate word start time relative to the dialogue line start (start_time_chunk)
            if i == chunk_start_index:
                # Delay from Dialogue Start (start_time_chunk) to the word's actual start
                delay_from_start_s = (
                    word_start + config.SUBTITLE_START_DELAY_SECONDS
                ) - start_time_chunk
                delay_from_start_cs = max(0, round(delay_from_start_s * 100))
                karaoke_text += f"{{\\k{delay_from_start_cs}}}"
            else:
                karaoke_text += f"{{\\k{config.WORD_DELAY_CS}}}"

            karaoke_text += (
                f"{{\\kf{duration_cs}"
                f"\\1c{config.HIGHLIGHT_COLOR}}}"
                f"{word_text}"
                f"{{\\1c{config.BASE_COLOR}}} "
            )

        karaoke_text = karaoke_text.strip()

        # --- Create Dialogue Line ---
        fade_in = 20
        # Calculate fade out time relative to the line's visual duration
        fade_out = max(20, int((end_time_chunk - start_time_chunk) * 500 * 0.8))

        dialogue_line = (
            f"Dialogue: 0,{start_ass},{end_ass},CenterWord,,0,0,0,,"
            f"{{\\fad({fade_in},{fade_out})\\bord{config.BORDER_SIZE}\\blur{config.BLUR_RADIUS}}}{karaoke_text}\n"
        )
        ass_dialogues.append(dialogue_line)
        word_pointer = chunk_end_index

    ass += "".join(ass_dialogues)
    ass_path.write_text(ass, encoding="utf-8")
    print(f"✅ ASS script saved for {rashi}.")

    # 5. Execute FFMPEG Command for Subtitling and Trimming

    ass_filter_path_escaped = (
        str(ass_path.resolve()).replace("\\", "\\\\").replace(":", "\\:")
    )
    ass_filter_arg = f"ass='{ass_filter_path_escaped}'"

    # --- FFmpeg Command for Subtitling, Start Offset, and Trimming ---
    cmd = [
        "ffmpeg",
        "-y",
        # Input 1 (Video)
        "-i", str(rashi_video_input.resolve()),
        # Input 2 (Audio)
        "-i", str(audio_path.resolve()),
        # Video filter
        "-vf", ass_filter_arg,
        # Audio filter: Add silence at the start
        "-filter_complex",
        f"[1:a]adelay={int(config.SUBTITLE_START_DELAY_SECONDS * 1000)}|{int(config.SUBTITLE_START_DELAY_SECONDS * 1000)}[a]",
        # Map streams
        "-map", "0:v:0",
        "-map", "[a]",
        # Duration control
        "-t", f"{final_output_duration:.3f}",
        # Encoding settings
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(segment_output_path),
    ]

    try:
        utils.run_ffmpeg_command(cmd, f"Video Segment Generation: {rashi}")
        ass_path.unlink(missing_ok=True) # Clean up ASS file
        return segment_output_path
    except Exception as e:
        print(f"🛑 Video Segment Generation Failed for {rashi}: {e}")
        return None

# ================================================================
#           --- 7. FINAL MERGE STEP ---
# ================================================================

def final_video_merge(
    all_rashi_video_paths: list[Path], tmp_dir: Path, output_dir: Path, date_str_format: str
) -> bool:
    """
    Merges all successfully generated Rashi videos into one final video.
    """
    if len(all_rashi_video_paths) <= 1:
        return False

    # 1. Create the concatenation list file
    concat_list_file = tmp_dir / "final_concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for path in all_rashi_video_paths:
            f.write(f"file '{path.as_posix()}'\n")

    final_output_video = output_dir / f"Final_Rashifal_{date_str_format}.mp4"

    # 2. FFmpeg Concatenation Command (using the concat demuxer)
    merge_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list_file),
        "-c", "copy",  # Fast and lossless merging since all videos are already encoded
        str(final_output_video),
    ]

    try:
        utils.run_ffmpeg_command(merge_cmd, "FINAL VIDEO MERGE")
        print(f"\n✨ **COMPLETE VIDEO GENERATED:** {final_output_video.resolve()}")
        # Clean up the concat list
        concat_list_file.unlink(missing_ok=True)
        return True

    except Exception as e:
        print(f"🛑 FINAL VIDEO MERGE FAILED: {e}")
        concat_list_file.unlink(missing_ok=True)
        return False