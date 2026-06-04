#!/usr/bin/env python

# --- AGGRESSIVE WARNING/LOGGING SUPPRESSION ---
import os
import warnings
import logging
import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta
import datetime as dt # For use in YouTube metadata

# 1. Environment variable for Transformers (often works best for startup warnings)
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "true"

# 2. Suppress the specific UserWarning
warnings.filterwarnings(
    "ignore",
    message="The attention mask is not set and cannot be inferred from input because pad token is same as eos token.",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message="In 2.9, this function's implementation will be changed to use torchaudio.load_with_torchcodec",
    category=UserWarning,
)
warnings.filterwarnings("ignore", category=FutureWarning)

import warnings

warnings.filterwarnings(
    "ignore",
    message="Failed to launch Triton kernels, likely due to missing CUDA toolkit; falling back to",
    category=UserWarning,
)


# 3. Silence general library logs (optional, but helpful)
logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
logging.getLogger("TTS").setLevel(logging.ERROR)
# ---------------------------------------------


# --- Internal Module Imports ---
import config
import datamodel
import generator
import utils # Contains split_text_safe, run_ffmpeg_command
import videopipeline # Contains generate_video_segment, final_video_merge
import upload # Contains upload_to_youtube

# --- Third-party heavy imports (PyTorch/TTS) ---
try:
    import torch
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
    from TTS.config.shared_configs import BaseDatasetConfig
    from TTS.api import TTS

    # Safely adding globals for PyTorch unpickling
    torch.serialization.add_safe_globals(
        [XttsConfig, XttsAudioConfig, XttsArgs, BaseDatasetConfig]
    )
except ImportError:
    print("🚨 Critical Error: TTS/PyTorch libraries are missing.")
    sys.exit(1)
except NameError: # Catch if classes aren't defined in this version
    pass
except Exception:
    pass # Continue to allow TTS loading to fail later


def main(test_mode=False):
    
    # --- START OVERALL TIMER ---
    overall_start_time = time.time()
    # ---------------------------

    # Decide device once
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🧠 Using device: {device}")

    # 1. Setup: Load Data, History, and Directories
    rashifal_data = datamodel.get_categorized_data()
    today = datetime.now().date()
    
    # --- History Setup Logic (Moved from setup_history function) ---
    HISTORY_PATH = config.used_history_file
    MAX_HISTORY_DAYS = config.MAX_HISTORY_DAYS
    
    # ... (History loading and cleaning logic remains here) ...
    if HISTORY_PATH.exists():
        try:
            used_history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("⚠️ History file corrupted — resetting.")
            used_history = {}
    else:
        used_history = {}

    cutoff_date = today - timedelta(days=MAX_HISTORY_DAYS)
    for rashi, entries in list(used_history.items()):
        if not isinstance(entries, list):
            used_history[rashi] = []
            continue
        used_history[rashi] = [
            e
            for e in entries
            if isinstance(e, dict)
            and "date" in e
            and datetime.strptime(e["date"], "%Y-%m-%d").date() >= cutoff_date
        ]

    daily_rashifal = {}
    
    # --- Directory setup ---
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.tmp_dir.mkdir(parents=True, exist_ok=True)
    config.tts_text_dir.mkdir(exist_ok=True)


    # 2. Text Generation and History Update
    for rashi in config.rashis:
        chosen_text = generator.generate_rashifal_text(rashi, rashifal_data)
        daily_rashifal[rashi] = chosen_text
        used_history.setdefault(rashi, []).append({"text": chosen_text, "date": str(today)})

    config.used_history_file.write_text(
        json.dumps(used_history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"🧠 Updated {len(used_history)} rashis in history. Generating TTS now.")

    
    # 3. TTS Model Initialization
    print(f"Loading TTS model: {config.tts_model}...")
    try:
        tts = TTS(config.tts_model)
        # Move model to GPU if available
        if device == "cuda":
            try:
                tts.to(device)
                print("✅ XTTS moved to GPU.")
            except AttributeError:
                print("⚠️ This TTS version doesn't support .to(); staying on CPU.")
                device = "cpu"
    except Exception as e:
        print(f"🚨 Error loading TTS model: {e}")
        sys.exit(1)

    rashi_list = [config.rashis[0]] if test_mode else config.rashis
    generated_count = 0
    all_rashi_video_paths = []

    # 4. Main Generation Loop (TTS and Audio/Video Segment Creation)
    for rashi in rashi_list:
        # Check for Rashi video file presence
        video_number = config.RASHI_TO_VIDEO_MAP.get(rashi)
        rashi_video_input = config.RASHI_VIDEO_DIR / f"{video_number}{config.RASHI_VIDEO_EXTENSION}"
        
        if not video_number or not rashi_video_input.exists():
            print(
                f"🚨 ERROR: Input video for {rashi} (expected {video_number}{config.RASHI_VIDEO_EXTENSION}) not found. Skipping."
            )
            continue

        text = daily_rashifal[rashi]
        chunks = utils.split_text_safe(text, max_len=200)

        if test_mode and rashi == rashi_list[0]:
            chunks = [chunks[0]]
            print("⚡ Test mode: generating only the first chunk of the first rashi.")

        temp_files = []

        # --- 4a. Generate Chunks Audio & Text ---
        for i, chunk in enumerate(chunks):
            out_file = config.tmp_dir / f"{rashi}_{i}.wav"
            txt_file = config.tts_text_dir / f"{rashi}_{i}.txt"
            txt_file.write_text(chunk, encoding="utf-8")

            print(f"🎼 Generating TTS for {rashi}, chunk {i + 1}/{len(chunks)}...")

            try:
                tts.tts_to_file(
                    text=chunk,
                    speaker_wav=config.speaker_wav,
                    language="hi",
                    file_path=str(out_file),
                )
            except Exception as e:
                print(f"🛑 TTS failed for {rashi} chunk {i}: {e}. Skipping chunk.")
                continue

            if not out_file.exists() or out_file.stat().st_size == 0:
                print(
                    f"Warning: TTS output missing or zero-length for {rashi}_{i}. Skipping chunk."
                )
                continue
            temp_files.append(str(out_file))

        # --- 4b. Merge chunks per rashi to get the final Rashi AUDIO file ---
        if not temp_files:
            continue
            
        rashi_concat_file = config.tmp_dir / f"{rashi}_concat.txt"
        with open(rashi_concat_file, "w", encoding="utf-8") as f:
            for wav in temp_files:
                # FIX: Explicitly use 'pathlib.Path' to resolve UnboundLocalError
                f.write(f"file '{Path(wav).as_posix()}'\n")

        # The final audio file for this Rashi
        rashi_audio_path = config.tmp_dir / f"{rashi}.wav"
        rashi_text_path = config.tts_text_dir / f"{rashi}.txt"
        rashi_text_path.write_text(
            "\n\n".join(chunks), encoding="utf-8"
        ) # Save combined text

        # FFmpeg command to concatenate audio chunks
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(rashi_concat_file),
            "-af", "volume=4.0,dynaudnorm=f=75", "-c:a", "pcm_s16le", str(rashi_audio_path),
        ]
        try:
            utils.run_ffmpeg_command(cmd, f"Rashi Chunk Merge: {rashi}")
        except Exception:
            print(f"❌ Failed to merge chunks for {rashi}. Skipping this rashi.")
            if test_mode:
                sys.exit(1)
            continue

        # --- GENERATE FINAL VIDEO FOR THIS RASHI (using videopipeline module) ---
        video_segment_path = videopipeline.generate_video_segment(
            rashi_audio_path, rashi_text_path, config.output_dir, rashi
        )
        if video_segment_path and video_segment_path.exists():
            print(f"🎉 FINAL VIDEO SEGMENT GENERATED: {video_segment_path.name}\n")
            generated_count += 1
            all_rashi_video_paths.append(video_segment_path) # <<< COLLECT PATH

        # Clean up temporary files for this Rashi
        rashi_concat_file.unlink(missing_ok=True)
        for f in temp_files:
            Path(f).unlink(missing_ok=True)
        rashi_audio_path.unlink(missing_ok=True)
        rashi_text_path.unlink(missing_ok=True)

        if test_mode:
            break

    # 5. FINAL MERGE STEP
    final_output_video = videopipeline.final_video_merge(all_rashi_video_paths)
    final_merge_successful = final_output_video and final_output_video.exists()

    # 6. YOUTUBE UPLOAD
    if final_merge_successful:
        try:
            # --- Automatically set YouTube metadata ---
            today_str = config.today_str # Use pre-defined string
            video_title = (
                f"🪔 आज का राशिफल | {today_str} | सभी 12 राशियों का दैनिक भविष्यफल"
            )

            video_description = f"""
🪔 {today_str} का राशिफल | आज का राशिफल | दैनिक भविष्यफल

🌟 जानिए आपकी राशि आज क्या कहती है!
... (Full description text as defined previously) ...
"""
            tags = [
                "rashifal", "daily horoscope", "astrology", "zodiac", "hindi rashifal", 
                "aaj ka rashifal", "today horoscope", "vedic astrology", "aajkarashifal", 
                "rashiphal", "bhavishyavani", "sanatan dharma", "astro tak",
            ]

            # ✅ Upload final merged Rashifal video
            upload.upload_to_youtube(
                final_output_video,
                video_title,
                video_description,
                tags,
                privacy="public",
                test_mode=test_mode,
            )

        except Exception as e:
            print(f"⚠️ YouTube upload skipped or failed: {e}")

    # 7. Cleanup individual Rashi video segments
    if final_merge_successful:
        print("\n🧹 Cleaning up individual Rashi video segments...")
        for path in all_rashi_video_paths:
            if path != final_output_video: # Avoid deleting the single video if only one was generated
                try:
                    path.unlink(missing_ok=True)
                except OSError as e:
                    print(f"    ⚠️ Could not delete temporary video segment {path.name}: {e}")

    print(
        f"\n✨ Script finished. Generated {generated_count} individual Rashi videos in {config.FINAL_VIDEO_BASE_DIR.resolve()}."
    )

    # --- CALCULATE AND PRINT FINAL TIME ---
    overall_end_time = time.time()
    total_execution_time = overall_end_time - overall_start_time

    print(
        f"\n======================================================="
    )
    print(
        f"⏱️ TOTAL EXECUTION TIME: {total_execution_time:.2f} seconds"
    )
    print(
        f"======================================================="
    )
    # ----------------------------------------


# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate daily rashifal video from TTS and subtitles."
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (no YouTube upload; processes only the first chunk of the first rashi).",
    )
    args = parser.parse_args()
    main(test_mode=args.test)