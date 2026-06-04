# src/text_gen.py
from google import genai
from google.genai import types
from .config import Config
from .utils import save_text
import re

# IMPORTANT: You must implement this function in your .utils file
def load_riddle_history(filepath):
    """Loads a list of previously generated, cleaned riddles."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Reads all lines, strips whitespace, and removes the CTA for better comparison
            history = [
                line.strip().replace(" - उत्तर पता हो तो कमेंट करें", "")
                for line in f if line.strip()
            ]
        # Return only a few (e.g., the last 10) to save context window space
        return history[-10:] 
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"History load error: {e}")
        return []


class TextGenerator:
    def __init__(self):
        print("🧠 Initializing Gemini...")
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

    def remove_answer_spoilers(self, text):
        """Clean up text to preserve Hindi numbered lists and remove spoilers/English."""
        
        # 1. Remove parenthetical content (often spoilers/English explanations)
        text = re.sub(r'\(.*?\)', '', text)
        
        # 2. Filter lines containing spoiler words
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            if "answer" in line.lower() or "उत्तर" in line.lower():
                continue
            clean_lines.append(line)
        
        text = "\n".join(clean_lines)

        # 3. Aggressively remove stray English letters (a-z, A-Z)
        text = re.sub(r'[a-zA-Z]', '', text) 
        
        # 4. Remove punctuation that can cause TTS pauses/confusion.
        # We must keep '.' (dot) for the numbering (e.g., 1.)
        bad_chars = ["?", "!", ":", "\"", "'", "|", "*", "।"] 
        for c in bad_chars:
            text = text.replace(c, "")
            
        # 5. Clean up extra spaces
        text = text.replace("  ", " ").strip()
        
        # 6. Ensure lines are clean and non-empty
        return "\n".join([line.strip() for line in text.split('\n') if line.strip()])

    def generate_riddle(self):
        print("📝 Generating 5 Psychological Facts List...")


        # ----------------------------------------------------
        # NEW: Load previous riddles to avoid repetition
        # ----------------------------------------------------
        past_riddles = load_riddle_history(Config.FILES["RIDDLE"])
        
        if past_riddles:
            # Create a strong constraint string from the history
            history_constraint = "DO NOT generate any of the following riddles or ones that solve to the same answer: "
            # Join the last 5-10 riddles for the model to reference
            history_constraint += " | ".join(past_riddles)
        else:
            history_constraint = "Generate a completely new and unique riddle."
        # ----------------------------------------------------


        # Automatic Call-To-Action (Modified for list-style content)
        cta_text = "क्या आप इस बात से सहमत हैं? कमेंट करें"

        # --- UPDATED SYSTEM INSTRUCTION FOR 5 POINTS (Added Hindi only enforcement) ---
        sys_instruction = (
            "You are a Hindi Psychological Fact List Generator for Social Media. "
            "OUTPUT LANGUAGE: HINDI (Devanagari Script) ONLY. **DO NOT use any English words or markers.** "
            "Length: VERY SHORT (Max 60 words total across 5 points). "
            "Format: Must be a **numbered list of 5 concise points (1. to 5.)**. "
            "Style: Directly address the audience (using 'आप' or similar). "
            "Tone: Deep, Mysterious, and highly shareable. Focus on hidden signs, dark psychology, or intense emotions. "
            "Rule: Do NOT provide a conclusion or a summary at the end."
        )

        # --- FIXED PROMPT FOR VARIETY ---
        prompt = (
            "5 बहुत छोटे, पेचीदा मनोवैज्ञानिक तथ्य या इंसान के व्यवहार के संकेत हिंदी में लिखिए। "
            "हर पॉइंट एक लाइन का हो। "
            # 👇 CHANGE THIS LINE 👇
            "विषय: 'सच्ची मोहब्बत', 'छिपी हुई ताकत', 'मनोवैज्ञानिक संकेत', 'इंसानी व्यवहार के गहरे रहस्य', या 'किसी के व्यक्तित्व के छुपे सच' में से **कोई भी एक विषय चुनें** और उस पर केंद्रित रहें। "
            # 👆 CHANGE THIS LINE 👆
            "पहले एक आकर्षक Title लिखें और फिर 1. 2. 3. 4. 5. में पॉइंट्स लिखें।"
        )

        try:
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    temperature=0.7, 
                ),
            )

            if response.text:
                raw_text = response.text.strip()
                
                # Use adjusted cleaner for numbered lists and TTS prep
                clean_text = self.remove_answer_spoilers(raw_text) 
                
                # Combine clean text with CTA, separated by a line break for chunking
                final_text = f"{clean_text}\n\n{cta_text}" 

                save_text(Config.FILES["RIDDLE"], final_text)
                print(f"✅ Fact List Saved: {final_text[:50]}...")
                return final_text

            return None

        except Exception as e:
            print(f"❌ Gemini Fact List Error: {e}")
            return None

    # ... (generate_image_prompt method remains the same) ...
    def generate_image_prompt(self, riddle_text):
        print("🖼️ Generating Realistic Image Prompt...")

        # ... (rest of the generate_image_prompt method) ...
        
        # IMPORTANT: Ensure the final output is cleaned of extra list markers or titles
        # by only taking the *body* of the riddle_text for image generation focus.
        # This prevents the image prompt from being based on the CTA line.
        lines = riddle_text.split('\n')
        theme_text = "\n".join([line for line in lines if "कमेंट करें" not in line])
        
        # --- UPDATED SYSTEM INSTRUCTION FOR IMAGE PROMPT ---
        sys_instruction = (
            "You are an expert AI Art Director. "
            "Task: Generate visual keywords for a PHOTOREALISTIC, CINEMATIC image based on the **emotional theme** of the provided list of facts. "
            "Style: Unreal Engine 5, 8k, Octane Render, Dramatic Lighting, Hyper-realistic, Focus on **mood and atmosphere** (e.g., loneliness, intense love, secret fear). "
            "Content: Close-up of a person's hands or silhouette in a specific emotional setting. "
            "Negative: No text, no watermark, no cartoons, no drawings, no abstract shapes."
            "Format: Comma-separated list. Limit 12 keywords."
        )

        # --- UPDATED PROMPT ---
        prompt = f"Fact List Theme: '{theme_text}'. Visual keywords for a realistic 8k image that captures the deep emotional mood of the list:"

        try:
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    temperature=0.4, 
                ),
            )

            if response.text:
                # ... (rest of the image prompt cleaning logic) ...
                img_prompt = response.text.strip().replace("\n", ", ")
                
                for marker in ["prompt:", "keywords:", "output:", "visual keywords:"]:
                    if marker in img_prompt.lower():
                        img_prompt = img_prompt.split(marker)[-1].strip()

                img_prompt = img_prompt[:120].strip(" ,")

                save_text(Config.FILES["PROMPT"], img_prompt)
                print(f"🎨 Image Prompt Saved: {img_prompt}")
                return img_prompt

            return None

        except Exception as e:
            print(f"❌ Gemini Prompt Error: {e}")
            return None