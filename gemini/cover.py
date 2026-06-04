import torch
from diffusers import StableDiffusionPipeline, LCMScheduler

def generate_marketing_cover():
    print("🚀 Initializing Generator for Gumroad Cover...")
    
    # 1. Load the Model
    model_id = "runwayml/stable-diffusion-v1-5"
    lcm_lora_id = "latent-consistency/lcm-lora-sdv1-5"
    
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id, torch_dtype=torch.float16, variant="fp16", safety_checker=None
    )
    pipe.load_lora_weights(lcm_lora_id)
    pipe.fuse_lora()
    pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
    
    if torch.cuda.is_available():
        pipe.to("cuda")
    else:
        print("⚠️ Slow CPU Mode")

    # 2. Marketing Prompt (Futuristic & High Tech)
    # This prompt is designed to sell "AI Automation"
    prompt = (
        "futuristic ai artificial intelligence brain glowing interface, "
        "digital neural network background, "
        "cinematic lighting, hyper-realistic, 8k, "
        "unreal engine 5, wide angle shot, "
        "cyberpunk colors, deep blue and gold, highly detailed, "
        "technology, automation, coding script aesthetic"
    )
    
    negative_prompt = "text, watermark, blurry, low quality, distortion, ugly, vertical"

    print("🎨 Generating 16:9 Cover Image...")
    
    # 3. Generate 16:9 (912x512 is the safe max for SD 1.5)
    # You will stretch this to 1280x720 later.
    image = pipe(
        prompt=prompt,
        width=912, 
        height=512,
        num_inference_steps=8,
        guidance_scale=2.0,
        negative_prompt=negative_prompt
    ).images[0]
    
    # 4. Save
    output_path = "output/gumroad_cover.png"
    # PIL saves at 72 DPI by default
    image.save(output_path)
    print(f"✅ Cover Image Saved: {output_path}")
    print("👉 NOTE: Use Canva or Paint to resize this from 912x512 to 1280x720!")

if __name__ == "__main__":
    generate_marketing_cover()