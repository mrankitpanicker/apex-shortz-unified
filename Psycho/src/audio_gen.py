# src/audio_gen.py
import os
import torch
import re
import warnings
from .config import Config


class AudioGenerator:
    def __init__(self):
        try:
            from TTS.api import TTS
            from TTS.tts.configs.xtts_config import XttsConfig
            from TTS.tts.models.xtts import XttsAudioConfig
            from TTS.tts.models.xtts import XttsArgs
            from TTS.config.shared_configs import BaseDatasetConfig

            torch.serialization.add_safe_globals([
                XttsConfig, XttsAudioConfig, XttsArgs, BaseDatasetConfig
            ])

            self.TTS_Class = TTS
            self.gpu = torch.cuda.is_available()

            # Ordinal Mapping (For list markers 1. 2. 3...)
            self.HINDI_ORDINALS = {
                1: 'पहला', 2: 'दूसरा', 3: 'तीसरा', 4: 'चौथा', 5: 'पांचवा',
                6: 'छठा', 7: 'सातवा', 8: 'आठवां', 9: 'नवां', 10: 'दसवां'
            }

        except ImportError:
            print("❌ TTS Library missing. Install: pip install \"TTS[all]\"")
            self.TTS_Class = None
            self.HINDI_ORDINALS = {}

        self.tts_instance = None  # Lazy load

    # --------------------------------------------------------
    # LOAD TTS MODEL ONCE (IMPORTANT)
    # --------------------------------------------------------

    def _load_tts(self):
        if self.tts_instance is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"🧠 Using device for XTTS: {device}")

            # Load TTS with GPU flag if available
            self.tts_instance = self.TTS_Class(
                "tts_models/multilingual/multi-dataset/xtts_v2",
                gpu=(device == "cuda")
            )

            # Some versions require manual .to(), others ignore it safely
            if device == "cuda":
                try:
                    self.tts_instance.to("cuda")
                    print("⚡ XTTS moved to GPU.")
                except Exception:
                    print("⚠️ XTTS does not support .to(); staying on CPU.")

    # --------------------------------------------------------
    # NUMBER CONVERSION (Removed Cardinal Logic) + LIST NUMBER FIX
    # --------------------------------------------------------
    def _convert_numbers_to_words(self, text):
        # Original number_to_hindi function (for cardinal numbers) is removed.

        # Mask list numbers like "1. text"
        masked_text = re.sub(
            r'^(\d{1,3})\.\s',
            lambda m: f"__LIST_NUMBER_{m.group(1)}__ ",
            text,
            flags=re.MULTILINE
        )

        # Convert standalone 1–999 (Returns original number as-is, since HINDI_NUMBERS is removed)
        def replace_match(m):
            return m.group(0)

        converted_text = re.sub(r'\b\d{1,3}\b', replace_match, masked_text)

        # Restore list number (Arabic)
        subtitle_text = re.sub(
            r'__LIST_NUMBER_(\d{1,3})__\s',
            lambda m: f"{m.group(1)}. ",
            converted_text
        )

        # Restore list number (Hindi ORDINAL words: पहला, दूसरा, etc.)
        def ordinal_to_hindi(m):
            num = int(m.group(1))
            word = self.HINDI_ORDINALS.get(num)
            if word:
                return f"{word} "
            return f"{num} " # Fallback to Arabic numeral if ordinal not mapped

        tts_text = re.sub(
            r'__LIST_NUMBER_(\d{1,3})__\s',
            ordinal_to_hindi,
            converted_text
        )

        return tts_text.strip(), subtitle_text.strip()

    # --------------------------------------------------------
    # FIXED — REMOVE STANDALONE PUNCTUATION CHUNKS
    # --------------------------------------------------------
    def _chunk_text(self, text, max_chars=250):
        raw = [line.strip() for line in text.split("\n") if line.strip()]

        chunks = []
        for line in raw:

            # 1. Remove lines that are ONLY punctuation (e.g., !!! or ??? or ----)
            if re.fullmatch(r'[^\w\d\u0900-\u097F]+', line):
                continue

            # 2. Remove single punctuation at start or end
            line = re.sub(r'^[^\w\d\u0900-\u097F]+', '', line).strip()
            line = re.sub(r'[^\w\d\u0900-\u097F]+$', '', line).strip()

            if not line:
                continue

            chunks.append(line)

        # Final safety
        if chunks and re.fullmatch(r'[^\w\d\u0900-\u097F]', chunks[0]):
            chunks.pop(0)

        return chunks


    # --------------------------------------------------------
    # CLEAN SUBTITLES (PRESERVE ALIGNMENT)
    # --------------------------------------------------------
    def clean_text_for_subtitles(self, subs):
        cleaned = []

        for s in subs:
            # Remove all periods (still helpful for clean subtitles)
            s = s.replace(".", "")

            # Remove trailing : ; , 
            s = re.sub(r'[,;:]$', '', s).strip()

            cleaned.append(s)

        return cleaned

    # --------------------------------------------------------
    # MAIN FUNCTION
    # --------------------------------------------------------
    def generate(self, text):
        if not self.TTS_Class:
            return [], []

        print("🔊 Generating Audio (XTTS)...")

        if not os.path.exists(Config.FILES["REF_AUDIO"]):
            print("❌ Missing ref.wav")
            return [], []

        # 1. Numbers → Hindi (for TTS) and subtitle-safe version
        tts_text, subtitle_text = self._convert_numbers_to_words(text)

        # --------------------------------------------------------
        # FINAL LINE CLEANING BEFORE CHUNKING
        # --------------------------------------------------------
        def clean_lines(lines):
            cleaned = []
            for line in lines.split("\n"):
                line = line.strip()

                # remove empty
                if not line:
                    continue

                # remove standalone punctuation
                if re.fullmatch(r'[^\w\d\u0900-\u097F]+', line):
                    continue

                # strip leading punctuation
                line = re.sub(r'^[^\w\d\u0900-\u097F]+', '', line).strip()

                # strip trailing punctuation
                line = re.sub(r'[^\w\d\u0900-\u097F]+$', '', line).strip()

                if line:
                    cleaned.append(line)

            return "\n".join(cleaned)

        # Apply cleaning BEFORE chunking
        clean_tts_text = clean_lines(tts_text)
        clean_subtitle_text = clean_lines(subtitle_text)

        # --------------------------------------------------------
        # 🔑 MODIFIED: Strip Title/Header Line and CTA Before Chunking 🔑
        # --------------------------------------------------------
        
        tts_lines = clean_tts_text.split('\n')
        sub_lines = clean_subtitle_text.split('\n')
        
        # Safely remove the first line if it's the non-numbered header
        if tts_lines and not re.match(r'^\d\.', tts_lines[0].strip()):
            tts_lines.pop(0)
            sub_lines.pop(0)
        
        # Safely remove the CTA line(s) from the end if they don't look like facts
        while sub_lines and not re.match(r'^\d\.', sub_lines[-1].strip()):
            if len(tts_lines) > 1: # Prevent popping the last fact if it's the only one
                tts_lines.pop(-1)
                sub_lines.pop(-1)
            else:
                break


        # Recombine the facts-only content
        tts_facts_only = "\n".join(tts_lines)
        subtitle_facts_only = "\n".join(sub_lines)
        
        # 2. Clean chunking
        tts_chunks = self._chunk_text(tts_facts_only)
        subtitle_chunks = self._chunk_text(subtitle_facts_only)

        if not tts_chunks:
            print("❌ No valid chunks.")
            return [], []

        print(f"📝 Text split into {len(tts_chunks)} audio chunks.")

        # Load XTTS once
        self._load_tts()
        tts = self.tts_instance

        out_paths = []
        base, ext = os.path.splitext(Config.FILES["AUDIO_OUT"])

        # 3. Generate each chunk
        for i, chunk in enumerate(tts_chunks):
            idx = i + 1
            file_path = f"{base}_chunk{idx}{ext}"

            print(f"\n🔊 Generating Chunk {idx}: '{chunk[:30]}...'")

            # Passing the chunk directly without the period buffer
            tts_input = chunk

            tts.tts_to_file(
                text=tts_input,
                file_path=file_path,
                speaker_wav=Config.FILES["REF_AUDIO"],
                language="hi"
            )

            out_paths.append(file_path)

        print(f"\n✅ Audio for {len(out_paths)} chunks saved.")

        # 4. Final subtitles
        cleaned_subs = self.clean_text_for_subtitles(subtitle_chunks)

        return out_paths, cleaned_subs