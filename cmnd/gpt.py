#!/usr/bin/env python
"""
Fixed and improved Rashifal TTS + ASS subtitle + MP4 generator.

Key fixes applied in this version:
- Ensure date_str_format is defined before use (prevents NameError).
- Better path handling with pathlib.Path and consistent forward slashes.
- Safer FFmpeg runner with captured output and helpful error prints.
- Fixed ASS karaoke loop: builds per-word karaoke tags correctly and computes centiseconds.
- Consistent timing values for hold/delay (milliseconds vs seconds corrected).
- Added lightweight helper implementations for missing utilities (get_wav_duration, split_text_safe,
  clean_text_for_timing). If you already have custom implementations, replace these.
- Fail-fast and user-friendly messages for missing dependencies (Whisper, TTS library, FFmpeg).

Note: This file assumes you have working Coqui TTS and OpenAI Whisper (or standalone whisper) installed
and FFmpeg available in PATH. Replace speaker_wav, tts_model, and input data with your real values.
"""

import json
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import List

# Optional imports; keep try/except to provide helpful errors
try:
    from TTS import TTS  # Coqui TTS (package name may differ)
except Exception:
    TTS = None

try:
    import whisper
except Exception:
    whisper = None

# ------------------------ Helper utilities ------------------------

def run_ffmpeg_command(cmd: List[str], label: str = "ffmpeg"):
    """Run ffmpeg command and print helpful output on error."""
    try:
        print(f"Running FFmpeg: {' '.join(cmd)}")
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if proc.stdout:
            print(proc.stdout)
        return proc
    except subprocess.CalledProcessError as e:
        print(f"ERROR ({label}): FFmpeg failed with return code {e.returncode}")
        if e.stdout:
            print("--- ffmpeg stdout ---")
            print(e.stdout)
        if e.stderr:
            print("--- ffmpeg stderr ---")
            print(e.stderr)
        raise


def get_wav_duration(path: Path) -> float:
    """Return duration of WAV (seconds) using ffprobe. Falls back to wave module for local WAVs."""
    path = Path(path)
    if not path.exists():
        return 0.0
    # Try ffprobe first (more robust)
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        out = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float(out.stdout.strip())
    except Exception:
        # Fallback: use wave module (only for PCM WAV)
        try:
            import wave

            with wave.open(str(path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / float(rate)
        except Exception:
            return 0.0


def split_text_safe(text: str, max_len: int = 200) -> List[str]:
    """Split text into approximate chunks without breaking punctuation too badly."""
    words = text.split()
    chunks = []
    cur = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + 1 > max_len and cur:
            chunks.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
        else:
            cur.append(w)
            cur_len += len(w) + 1
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def clean_text_for_timing(text: str) -> str:
    """Remove multiple spaces and normalize punctuation for timing-based splitting."""
    return re.sub(r"\s+", " ", text.strip())


# ------------------------ Main functions ------------------------

def generate_tts_and_merge_audio(
    rashis,
    daily_rashifal,
    tts_model,
    speaker_wav,
    output_dir: Path,
    tmp_dir: Path,
    HISTORY_PATH: Path,
    used_history: dict,
    date_str_format: str = None,
    final_output: Path = None,
    test_mode: bool = False,
):
    """Generate per-rashi TTS files, merge per-rashi chunks and optionally merge all rashis into final_output.

    Important: caller should create output_dir/tmp_dir and pass Paths.
    """
    # Ensure date string is present early to avoid use-before-def bugs
    if date_str_format is None:
        date_str_format = datetime.today().strftime("%Y_%m_%d")

    # Paths
    output_dir = Path(output_dir)
    tmp_dir = Path(tmp_dir)
    tts_text_dir = output_dir / "tts_chunks"

    output_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tts_text_dir.mkdir(parents=True, exist_ok=True)

    # Initialize TTS model
    print(f"Loading TTS model: {tts_model}...")
    if TTS is None:
        print("ERROR: TTS library not available. Install Coqui TTS or adjust imports.")
        sys.exit(1)
    try:
        tts = TTS(tts_model)
    except Exception as e:
        print(f"Error loading TTS model: {e}")
        print("Please ensure your environment is set up correctly for the Coqui TTS library.")
        sys.exit(1)

    wav_files = []
    full_spoken_text_chunks = []

    rashi_list = [rashis[0]] if test_mode else rashis

    for rashi in rashi_list:
        if rashi not in daily_rashifal:
            continue

        text = daily_rashifal[rashi]
        chunks = split_text_safe(text, max_len=200)

        if test_mode:
            chunks = [chunks[0]]
            print("⚡ Test mode: generating only the first chunk of the first rashi.")

        full_spoken_text_chunks.extend(chunks)

        temp_files = []

        for i, chunk in enumerate(chunks):
            out_file = tmp_dir / f"{rashi}_{i}.wav"
            txt_file = tts_text_dir / f"{rashi}_{i}.txt"
            txt_file.write_text(chunk, encoding="utf-8")

            print(f"🎼 Generating TTS for {rashi}, chunk {i+1}/{len(chunks)}...")

            if not Path(speaker_wav).exists():
                print(f"Error: Speaker WAV file not found at {speaker_wav}.")
                sys.exit(1)

            # Coqui TTS: using tts_to_file; adapt args as per your TTS API
            try:
                tts.tts_to_file(
                    text=chunk,
                    speaker_wav=str(speaker_wav),
                    language="hi",
                    file_path=str(out_file),
                )
            except Exception as e:
                print(f"TTS error for {rashi}_{i}: {e}")
                continue

            if not out_file.exists() or out_file.stat().st_size == 0:
                print(f"Warning: TTS output missing or zero-length for {rashi}_{i}. Skipping chunk.")
                continue

            temp_files.append(str(out_file))

        if not temp_files:
            continue

        rashi_concat_file = tmp_dir / f"{rashi}_concat.txt"
        with open(rashi_concat_file, "w", encoding="utf-8") as f:
            for wav in temp_files:
                f.write(f"file '{Path(wav).as_posix()}'\n")

        final_rashi_file = tmp_dir / f"{rashi}.wav"

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(rashi_concat_file),
            "-af",
            "volume=4.0,dynaudnorm=f=75",
            "-c:a",
            "pcm_s16le",
            str(final_rashi_file),
        ]

        try:
            run_ffmpeg_command(cmd, f"Rashi Chunk Merge: {rashi}")
        except Exception:
            print(f"❌ Failed to merge chunks for {rashi}. Skipping this rashi.")
            rashi_concat_file.unlink(missing_ok=True)
            if test_mode:
                sys.exit(1)
            continue

        rashi_concat_file.unlink(missing_ok=True)

        if test_mode:
            final_output = output_dir / f"{date_str_format}.wav"
            Path(final_rashi_file).replace(final_output)
            print(f"⚡ Test WAV generated: {final_output}")
            break
        else:
            wav_files.append(str(final_rashi_file))
            for f in temp_files:
                Path(f).unlink(missing_ok=True)

    # --- Date setup and final merge ---
    if final_output is None:
        final_output = output_dir / f"{date_str_format}.wav"

    if not test_mode and wav_files:
        concat_file = tmp_dir / "concat_all.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for wav in wav_files:
                f.write(f"file '{Path(wav).as_posix()}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-af",
            "volume=4.0,dynaudnorm=f=75",
            "-c:a",
            "pcm_s16le",
            str(final_output),
        ]

        try:
            run_ffmpeg_command(cmd, "Final All Rashi Merge")
        except Exception:
            print("❌ Critical failure: Final audio merge failed.")
            sys.exit(1)

        concat_file.unlink(missing_ok=True)
        for wav in wav_files:
            Path(wav).unlink(missing_ok=True)

        print(f"🎉 Final Rashifal WAV: {final_output}")

    elif test_mode:
        final_output = output_dir / f"{date_str_format}.wav"

    # --- Save full cleaned script
    if full_spoken_text_chunks:
        full_tts_script = "\n\n".join(full_spoken_text_chunks)
        script_file = output_dir / f"{date_str_format}.txt"
        script_file.write_text(full_tts_script, encoding="utf-8")
        print(f"📄 Full TTS script saved for reference: {script_file.name}")

    # --- Critical check
    if not final_output.exists() or get_wav_duration(final_output) == 0.0:
        print("\n\n🚨 CRITICAL ERROR: No final audio file was created or it has zero length. Exiting.")
        print(f"Please check the FFmpeg error details printed above for clues regarding file locking or path issues with: {final_output}")
        sys.exit(1)

    print("✅ TTS generation complete. Skipping subtitles and video creation.")
    return final_output


# ------------------------ Subtitle & Video generator ------------------------

def generate_subtitles_and_video(final_output: Path, output_dir: Path, date_str_format: str):
    tts_text_path = output_dir / f"{date_str_format}.txt"
    if not tts_text_path.exists():
        print(f"Error: Missing {tts_text_path}")
        sys.exit(1)
    tts_text = tts_text_path.read_text(encoding="utf-8")

    if not tts_text:
        print("Error: No spoken text was collected for subtitle generation. Exiting.")
        sys.exit(1)

    spoken_text_clean = clean_text_for_timing(tts_text)
    duration = get_wav_duration(final_output)

    words = spoken_text_clean.split()
    total_words = len(words)
    duration_per_word = duration / total_words if total_words > 0 else 0.5

    current_time = 0.0
    segment_list = []
    split_texts = re.split(r"(?<=[।!?])\s*", tts_text)

    for sentence in split_texts:
        sentence = sentence.strip()
        if not sentence:
            continue

        clean_sentence = clean_text_for_timing(sentence)
        num_words = len(clean_sentence.split())
        seg_duration = num_words * duration_per_word

        if current_time + seg_duration > duration:
            seg_duration = duration - current_time
            if seg_duration <= 0:
                break

        segment_list.append({"start": current_time, "end": current_time + seg_duration, "text": sentence})
        current_time += seg_duration

    print(f"Subtitles prepared for {len(segment_list)} segments. Total duration: {duration:.2f}s")

    # --- KINETIC ASS Script generation ---
    AUDIO_FILE_PATH = final_output
    TEXT_FILE_PATH = Path(output_dir) / f"{date_str_format}.txt"
    ASS_FILE_PATH = output_dir / f"{date_str_format}.ass"

    CHUNK_SIZE = 5  # words per display chunk

    def format_ass_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    try:
        total_duration_seconds = duration

        print(f"📄 Loading reference text from {TEXT_FILE_PATH}...")
        ref_text = TEXT_FILE_PATH.read_text(encoding="utf-8").strip()
        ref_words = ref_text.replace("\n", " ").split()
        print(f"Found {len(ref_words)} words in reference text.")

        if whisper is None:
            print("ERROR: whisper not installed. Install it or provide word timestamps some other way.")
            sys.exit(1)

        print("🎙️ Getting timestamps with whisper (tiny)...")
        model = whisper.load_model("tiny")
        result = model.transcribe(str(AUDIO_FILE_PATH), word_timestamps=True, language="hi")

        timestamps = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                if w.get("start") is not None and w.get("end") is not None and w.get("word"):
                    timestamps.append((w["start"], w["end"], w["word"].strip()))

        print(f"Whisper generated {len(timestamps)} word timestamps.")

        ass_header = """[Script Info]
Title: Hindi Word Sync
ScriptType: v4.00+
Collisions: Normal
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: CenterWord, Noto Sans Devanagari,150,&H00FFFF,&HFFFFFF,&H000000,&H000000,5,0,0,0,100,100,0,0,1,15,6,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        n = min(len(ref_words), len(timestamps))
        ass_dialogues = []

        word_pointer = 0
        while word_pointer < n:
            chunk_start_index = word_pointer
            chunk_end_index = min(word_pointer + CHUNK_SIZE, n)

            start_time_chunk = timestamps[chunk_start_index][0]
            end_time_chunk = timestamps[chunk_end_index - 1][1]

            # timings (seconds)
            hold_after_chunk = 0.35  # seconds to keep visible after last word
            delay_before_next = 0.15  # seconds of gap before next chunk

            end_time_chunk += hold_after_chunk
            if chunk_start_index != 0:
                start_time_chunk += delay_before_next

            start_ass = format_ass_time(start_time_chunk)
            end_ass = format_ass_time(end_time_chunk)

            # Build karaoke text by iterating words in this chunk
            karaoke_parts = []
            for i in range(chunk_start_index, chunk_end_index):
                word_start = timestamps[i][0]
                word_end = timestamps[i][1]
                word_text = timestamps[i][2]
                duration_cs = max(1, int(round((word_end - word_start) * 100)))

                # Create karaoke tag for this single word
                part = (
                    f"{{\\kf{duration_cs}\\1c&H00FFFF&\\blur2\\bord2"
                    f"\\t(0,100,\\fscx125\\fscy125\\bord5\\blur0\\1c&H00CCFF&)"
                    f"\\t(100,250,\\fscx100\\fscy100\\bord2\\blur2\\1c&H00FFFF&)}}{word_text}{{\\1c&HFFFFFF&}}"
                )
                karaoke_parts.append(part)

            karaoke_text = " ".join(karaoke_parts)

            fade_in_ms = 20
            fade_out_ms = max(20, int((end_time_chunk - start_time_chunk) * 500 * 0.8))

            dialogue_line = (
                f"Dialogue: 0,{start_ass},{end_ass},CenterWord,,0,0,0,,"
                f"{{\\fad({fade_in_ms},{fade_out_ms})\\bord6\\blur6}}{karaoke_text}\n"
            )
            ass_dialogues.append(dialogue_line)

            word_pointer = chunk_end_index

        ass = ass_header + "".join(ass_dialogues)

    except Exception as e:
        print(f"❌ Error while generating ASS subtitles: {e}")
        sys.exit(1)

    try:
        ASS_FILE_PATH.write_text(ass, encoding="utf-8")
        print(f"✅ Chunked, word-level synced ASS saved: {ASS_FILE_PATH.resolve()}")

        print("🎬 Generating test MP4 video with subtitles...")

        ass_path_str = Path(ASS_FILE_PATH).as_posix()
        escaped_ass_path = ass_path_str.replace(":", r"\\:")
        subtitles_filter_arg = f"ass='{escaped_ass_path}'"

        audio_input_path = str(final_output)
        video_output_path = output_dir / f"{date_str_format}.mp4"
        duration = get_wav_duration(final_output)

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=1280x720:d={duration}",
            "-i",
            audio_input_path,
            "-vf",
            subtitles_filter_arg,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(video_output_path),
        ]

        try:
            run_ffmpeg_command(cmd, "Final MP4 Video Generation")
            print(f"🎉 Final MP4 video generated: {video_output_path}")
        except Exception:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Unhandled error in main script: {e}")
        sys.exit(1)


# ------------------------ CLI entrypoint ------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tts", action="store_true", help="Skip TTS generation and directly generate video/subtitles")
    args = parser.parse_args()

    date_str_format = time.strftime("%Y_%m_%d")
    output_dir = Path("D:/tts/output/")
    output_dir.mkdir(parents=True, exist_ok=True)
    final_output = output_dir / f"{date_str_format}.wav"

    # Simple ffmpeg availability check
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print("FATAL: FFmpeg not found. Please install it or ensure it’s in your PATH.")
        sys.exit(1)

    if args.skip_tts:
        print("🎬 Skipping TTS generation. Using existing WAV and TXT for subtitle+video creation...")
        if not final_output.exists():
            print(f"❌ Audio not found: {final_output}")
            sys.exit(1)
        generate_subtitles_and_video(final_output, output_dir, date_str_format)
    else:
        print("🔊 Running full TTS generation and subtitle creation...")

        # Example data - replace with your real data pipeline
        rashis = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"]
        daily_rashifal = {"मेष": "आपका दिन बहुत शुभ रहेगा...", "वृषभ": "आज आपको धन लाभ हो सकता है।"}
        tts_model = "tts_models/multilingual/multi-dataset/xtts_v2"
        speaker_wav = Path("D:/tts/speaker_voice.wav")
        tmp_dir = Path("D:/tts/tmp/")
        HISTORY_PATH = Path("D:/tts/output/used_history.json")
        used_history = {}
        test_mode = False

        final_wav = generate_tts_and_merge_audio(
            rashis,
            daily_rashifal,
            tts_model,
            speaker_wav,
            output_dir,
            tmp_dir,
            HISTORY_PATH,
            used_history,
            date_str_format=date_str_format,
            final_output=final_output,
            test_mode=test_mode,
        )

        generate_subtitles_and_video(final_wav, output_dir, date_str_format)
