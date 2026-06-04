import random
import re
import datamodel # Import categorized data
import utils # Import helper functions

# ================================================================
# 1. LOGICAL TEXT GENERATION
# ================================================================

def generate_rashifal_text(rashi: str, data: dict) -> str:
    """
    Generates a structured, unique, and logically flowing horoscope script for a single Rashi.
    """

    # 1. Select phrases using random.choice
    p_status = random.choice(data["P_STATUS"])

    # Filter to avoid repetition: Ensure general/warning phrases are not identical to core status
    s_general_list = [s for s in data["S_GENERAL"] if s != p_status]
    s_general = random.choice(s_general_list)

    n_warning_list = [n for n in data["N_WARNING"]]
    n_warning = random.choice(n_warning_list)

    remedy = random.choice(data["REMEDIES"])
    ausp_color = random.choice(data["AUSP_COLORS"])
    luck_text = random.choice(data["LUCK_TEXTS"])

    # --- 2. Constructing the Script in Logical Segments ---

    # A. Opening
    opening = f" {rashi} राशि "

    # B. Core Status (P_STATUS)
    core_status = p_status

    # C. General Status (S_GENERAL) - Connected logically
    general_status_connector = random.choice(["वहीं, ", "इसके अलावा, "])
    general_status = general_status_connector + s_general

    # D. Challenge/Warning (N_WARNING) - Connected logically for contrast
    challenge_connector = random.choice(["हालांकि, ", "लेकिन, "])

    # Ensure N_WARNING doesn't have internal period/punctuation when inserted here
    challenge_advice = n_warning.strip()
    challenge_advice = re.sub(r"[।\.]\s*$", "", challenge_advice)

    challenge = challenge_connector + f"आज    {challenge_advice}। "

    # E. Remedy - Fixed template for clear introduction
    remedy_section = f"आपके लिए सलाह यह है कि {remedy}। "

    # F. Metrics - Fixed template
    metrics_section = f"आज का {ausp_color}। {luck_text}"

    # --- 3. Final Assembly ---
    final_script = (
        opening
        + core_status
        + " "
        + general_status
        + " "
        + challenge
        + remedy_section
        + metrics_section
    )

    # --- 4. Post-processing ---
    # Fix spacing and pronunciation after assembly
    final_script = utils.fix_hindi_pronunciation(final_script)
    # Convert percentage numbers to Hindi words for better TTS
    final_script = re.sub(r"(\d+)%", utils.convert_number_to_hindi, final_script)

    return final_script