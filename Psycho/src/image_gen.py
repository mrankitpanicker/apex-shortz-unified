import os
import logging
import warnings

# 1. IMMEDIATE SILENCE (Must be at the very top before other imports)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

# 2. Silence loggers and progress bars before they start
from huggingface_hub.utils import disable_progress_bars
disable_progress_bars()

import torch
from huggingface_hub import logging as hf_logging
from transformers import logging as transformers_logging
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from .config import Config

# Set global verbosity levels to ERROR only
transformers_logging.set_verbosity_error()
hf_logging.set_verbosity_error()
logging.getLogger("diffusers").setLevel(logging.ERROR)
logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=FutureWarning)

class ImageGenerator:
    def __init__(self):
        print("🚀 Initializing Stable Diffusion (Realistic Fast)...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🧠 ImageGenerator using device: {self.device} (RTX 3050)")
        self.pipe = self._load_pipeline()

    def _load_pipeline(self):
        try:
            model_id = "runwayml/stable-diffusion-v1-5"
            dtype = torch.float16 if self.device == "cuda" else torch.float32

            pipe = StableDiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=dtype,
                use_safetensors=True,
                safety_checker=None,
                requires_safety_checker=False,
                low_cpu_mem_usage=True, 
            )

            # Silence the final generation progress bar
            pipe.set_progress_bar_config(disable=True)
            pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)

            if self.device == "cuda":
                # RTX 3050 Optimal: Model Offload is faster than Sequential
                try:
                    pipe.enable_model_cpu_offload()
                except Exception:
                    pipe.enable_sequential_cpu_offload()

                # Optimized for 4GB VRAM
                try:
                    pipe.enable_xformers_memory_efficient_attention()
                except Exception:
                    pipe.enable_attention_slicing()
                
                pipe.vae.enable_tiling()
                print("⚡ GPU Performance Mode: Active.")
            
            return pipe

        except Exception as e:
            print(f"❌ SD Loading Error: {e}")
            return None

    def generate(self, prompt, seed=None):
        if self.device == "cuda":
            torch.cuda.empty_cache()

        if not self.pipe:
            print("❌ Error: Pipeline not initialized.")
            return None

        print("🎨 Drawing Realistic Image (Vertical)...")

        # Limit incoming text; style comes from SD_PROMPT_SUFFIX
        clean_prompt = prompt[:100]
        final_prompt = f"{clean_prompt}, {Config.SD_PROMPT_SUFFIX}"

        generator = torch.Generator(device=self.device)
        if seed is not None:
            generator.manual_seed(seed)
        else:
            generator.seed()

        try:
            image = self.pipe(
                prompt=final_prompt,
                width=448,          # Optimized for 4GB VRAM speed
                height=800,         # Vertical 9:16 aspect ratio
                num_inference_steps=14, 
                guidance_scale=6.5, 
                negative_prompt=Config.SD_NEGATIVE_PROMPT,
                generator=generator,
            ).images[0]

            image.save(Config.FILES["IMAGE_CLEAN"])
            print(f"✅ Image Saved to {Config.FILES['IMAGE_CLEAN']}")
            return Config.FILES["IMAGE_CLEAN"]

        except Exception as e:
            print(f"❌ Generation Error: {e}")
            return None