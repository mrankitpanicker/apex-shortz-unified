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
        """Clean up text to ensure no answers or brackets remain."""
        text = re.sub(r'\(.*?\)', '', text)
        lines = text.split('\n')
        clean_lines = []
        for line in lines:
            if "answer" in line.lower() or "उत्तर" in line.lower():
                continue
            clean_lines.append(line)
        text = " ".join(clean_lines)

        text = re.sub(r'[a-zA-Z]', '', text) 
        bad_chars = [",", ".", "?", "!", ":", "(", ")", "\"", "'", "|", "।"] 
        digits = list("0123456789०१२३४५६७८९")
        
        for c in bad_chars + digits:
            text = text.replace(c, "")
            
        return " ".join(text.split())

    def generate_riddle(self):
        print("📝 Generating Short & Tricky Hindi Riddle...")


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


        # Automatic Call-To-Action
        cta_text = "उत्तर पता हो तो कमेंट करें"

        sys_instruction = (
            "You are a Hindi Riddle Generator. "
            "OUTPUT LANGUAGE: HINDI (Devanagari Script) ONLY. "
            "Length: VERY SHORT (Max 20-30 words). "
            "Style: Male persona ('मैं'). "
            "Tone: Witty and tricky. "
            "Rule: Do NOT provide the answer."
        )

        prompt = (
            "एक बहुत छोटी और पेचीदा पहेली हिन्दी में लिखिए। "
            "यह 2 या 3 लाइनों से ज्यादा नहीं होनी चाहिए। "
            "शब्द आसान हों, लेकिन लॉजिक थोड़ा घुमावदार हो। "
            "वाक्यों के बीच में ' - ' (डैश) लगाएं। "
            "(Write a very short, tricky riddle. Max 2 lines.)"
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
                clean_text = self.remove_answer_spoilers(raw_text)
                
                if "-" not in clean_text:
                    words = clean_text.split()
                    chunked = [" ".join(words[i:i+4]) for i in range(0, len(words), 4)]
                    clean_text = " - ".join(chunked)

                final_text = f"{clean_text} - {cta_text}"

                save_text(Config.FILES["RIDDLE"], final_text)
                print(f"✅ Riddle Saved: {final_text[:50]}...")
                return final_text

            return None

        except Exception as e:
            print(f"❌ Gemini Riddle Error: {e}")
            return None

    def generate_image_prompt(self, riddle_text):
        print("🎨 Generating Realistic Image Prompt...")

        # CHANGED: Instructions for REALISM and CINEMATIC Lighting
        sys_instruction = (
            "You are an expert AI Art Director. "
            "Task: Generate visual keywords for a PHOTOREALISTIC, CINEMATIC image based on the riddle. "
            "Style: Unreal Engine 5, 8k, Octane Render, Dramatic Lighting, Hyper-realistic. "
            "Content: Close-up or Macro shot of the subject (or a hint to it). "
            "Negative: No text, no watermark, no cartoons, no drawings."
            "Format: Comma-separated list. Limit 12 keywords."
        )

        prompt = f"Riddle: '{riddle_text}'. Visual keywords for a realistic 8k image:"

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
                img_prompt = response.text.strip().replace("\n", ", ")
                
                for marker in ["prompt:", "keywords:", "output:"]:
                    if marker in img_prompt.lower():
                        img_prompt = img_prompt.split(marker)[-1].strip()

                img_prompt = img_prompt[:120].strip(" ,")

                save_text(Config.FILES["PROMPT"], img_prompt)
                print(f"✅ Image Prompt Saved: {img_prompt}")
                return img_prompt

            return None

        except Exception as e:
            print(f"❌ Gemini Prompt Error: {e}")
            return None