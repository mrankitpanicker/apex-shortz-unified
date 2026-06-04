# src/audio_gen.py
import os
import torch
from .config import Config


class AudioGenerator:
    def __init__(self):
        # PyTorch Safety Fix for XTTS
        try:
            from TTS.api import TTS
            from TTS.tts.configs.xtts_config import XttsConfig
            from TTS.tts.models.xtts import XttsAudioConfig
            from TTS.tts.models.xtts import XttsArgs
            from TTS.config.shared_configs import BaseDatasetConfig

            torch.serialization.add_safe_globals(
                [XttsConfig, XttsAudioConfig, XttsArgs, BaseDatasetConfig]
            )

            self.TTS_Class = TTS
            # Decide device once
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.gpu = self.device == "cuda"
            print(f"🧠 AudioGenerator using device: {self.device}")

        except ImportError:
            print("❌ TTS Library missing. Install with: pip install \"TTS[all]\"")
            self.TTS_Class = None
            self.device = "cpu"
            self.gpu = False

        # Lazy-loaded XTTS model instance
        self.tts_instance = None

    # --------------------------------------------------------
    # LOAD TTS MODEL ONCE (IMPORTANT)
    # --------------------------------------------------------
    def _load_tts(self):
        if self.tts_instance is None:
            if not self.TTS_Class:
                print("❌ Cannot load XTTS: TTS_Class is not available.")
                return

            print(f"🎛️ Loading XTTS v2 (gpu={self.gpu})...")
            self.tts_instance = self.TTS_Class(
                "tts_models/multilingual/multi-dataset/xtts_v2",
                gpu=self.gpu,
            )

            # Some versions support .to("cuda"), some already handle gpu internally
            if self.gpu:
                try:
                    self.tts_instance.to("cuda")
                    print("⚡ XTTS moved to GPU.")
                except Exception:
                    print("⚠️ XTTS .to('cuda') not supported; relying on internal gpu handling.")

    def generate(self, text: str):
        if not self.TTS_Class:
            return

        print("🔊 Generating Audio (XTTS)...")

        ref_audio = Config.FILES["REF_AUDIO"]
        out_audio = Config.FILES["AUDIO_OUT"]

        if not os.path.exists(ref_audio):
            print(f"❌ Missing ref.wav at {ref_audio}")
            return

        # Ensure model is loaded
        self._load_tts()
        if self.tts_instance is None:
            print("❌ XTTS instance could not be initialized.")
            return

        try:
            self.tts_instance.tts_to_file(
                text=text,
                file_path=out_audio,
                speaker_wav=ref_audio,
                language="hi",
            )
            print(f"✅ Audio saved at: {out_audio}")
        except Exception as e:
            print(f"❌ XTTS Error: {e}")
