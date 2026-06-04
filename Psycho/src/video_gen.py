# src/video_gen.py
import subprocess
import textwrap
import os 
import random
import json 
from .config import Config
from .utils import format_ass_time

class VideoEditor:
    # ... (_get_audio_duration method remains the same) ...
    def _get_audio_duration(self, audio_path):
        """
        Uses FFprobe (part of FFmpeg) to get the exact duration of an audio file.
        This replaces the need for the 'mutagen' library.
        """
        if not os.path.exists(audio_path):
            print(f"⚠️ Audio file not found: {audio_path}")
            return 0.0
            
        cmd = [
            'ffprobe', '-v', 'error', 
            '-show_entries', 'format=duration', 
            '-of', 'json', 
            audio_path
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            data = json.loads(result.stdout)
            
            duration_str = data.get('format', {}).get('duration')
            if duration_str:
                return float(duration_str)
            
            print(f"⚠️ Could not find duration in ffprobe output for {audio_path}.")
            return 0.0
            
        except subprocess.CalledProcessError as e:
            print(f"❌ FFprobe Error for {audio_path}: {e.stderr.strip()}")
            return 0.0
        except FileNotFoundError:
            print("❌ FFprobe not found. Ensure FFmpeg (which includes FFprobe) is installed and in your PATH.")
            return 0.0
        except json.JSONDecodeError:
            print(f"❌ Failed to parse ffprobe output for {audio_path}.")
            return 0.0

    # ... (_merge_audio method remains the same) ...
    def _merge_audio(self, audio_paths, output_path):
        """Merges multiple WAV files into a single output file using FFmpeg."""
        print(f"🎶 Merging {len(audio_paths)} audio chunks...")
        
        if len(audio_paths) == 1:
            print("➡️ Only one audio chunk found. Skipping merge.")
            os.rename(audio_paths[0], output_path) 
            return True
            
        list_file = os.path.join(os.path.dirname(output_path), "concat_list.txt")
        with open(list_file, "w") as f:
            for path in audio_paths:
                f.write(f"file '{path.replace(os.path.sep, '/')}'\n")

        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', 
            '-i', list_file, '-c', 'copy', output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            os.remove(list_file) 
            print(f"✅ Merged audio saved to: {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Audio Merge Failed. FFmpeg Code: {e.returncode}")
            return False

    # --- NO REDUNDANT CLASS DEFINITION HERE ---
    
    def create_subtitles(self, text_chunks, audio_paths):
        """
        Creates a single ASS subtitle file where each text chunk (fact)
        appears sequentially, timed to its corresponding audio chunk.
        Word-by-word random color (white/yellow) using inline ASS tags.
        Single font (Noto Sans Devanagari) to prevent dot/glyph rendering issues.
        """
        import random
        print("📝 Creating Word-by-Word Random Styled Subtitles...")

        # Single font only — prevents middle-dot rendering bug with mixed Devanagari fonts
        FONT = "Noto Sans Devanagari"

        # White and Yellow in ASS BGR hex format
        COLORS = [
            "&H00FFFFFF",  # White
            "&H0000FFFF",  # Yellow
        ]

        def styled_words(text):
            """
            Apply alternating random color to each word inline.
            Uses \\h (ASS hard space) between words to prevent dot artifacts.
            """
            words = text.split()
            styled = []
            last_color = None

            for word in words:
                # Ensure color never repeats consecutively
                available = [c for c in COLORS if c != last_color]
                color = random.choice(available)
                last_color = color

                tag = f"{{\\fn{FONT}\\c{color}}}"
                styled.append(f"{tag}{word}")

            # \\h = ASS hard space — prevents Unicode space being rendered as dot
            return "\\h".join(styled)

        # --- 1. Setup and Title Extraction ---
        total_duration = sum(self._get_audio_duration(p) for p in audio_paths)

        try:
            with open(Config.FILES["RIDDLE"], 'r', encoding='utf-8') as f:
                full_content = f.read()
                title_text = full_content.split('\n')[0].strip()
        except Exception:
            title_text = "शीर्षक उपलब्ध नहीं"

        header_ass = f"""[Script Info]
    Title: Gemini Pro
    ScriptType: v4.00+
    WrapStyle: 0
    ScaledBorderAndShadow: yes
    PlayResX: {Config.PLAY_RES_X}
    PlayResY: {Config.PLAY_RES_Y}
    YCbCr Matrix: None

    [V4+ Styles]
    Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
    Style: HeaderStyle,{Config.FONT_NAME},50,&H000000FF,&H00FFFFFF,&H00FFFFFF,&H80000000,1,0,0,0,90,100,0,0,1,3,1,8,50,50,40,1
    Style: BodyStyle,Noto Sans Devanagari,{Config.BODY_SIZE},&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,1.5,5,80,80,60,1


    [Events]
    Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
    """

        dialogues = []

        # Title displayed for full video duration — top-center, never bleeds
        dialogues.append(
            f"Dialogue: 0,0:00:00.00,{format_ass_time(total_duration)},HeaderStyle,,0,0,0,,{title_text}"
        )

        # --- 2. Generate Sequential Word-Styled Dialogue Events ---
        global_start_time = 0.0

        if len(text_chunks) != len(audio_paths):
            print(f"❌ Error: Mismatch between {len(text_chunks)} text chunks "
                f"and {len(audio_paths)} audio paths. Rendering may fail.")

        for i, (text_chunk, audio_path) in enumerate(zip(text_chunks, audio_paths)):
            chunk_duration = self._get_audio_duration(audio_path)

            if chunk_duration == 0:
                print(f"⚠️ शून्य ऑडियो अवधि के कारण चंक {i+1} को छोड़ दिया गया।")
                continue

            end_t = global_start_time + chunk_duration

            # Wrap into lines first, then apply per-word color styling
            lines = textwrap.wrap(text_chunk, width=28)
            styled_lines = [styled_words(line) for line in lines]
            final_text = "\\N".join(styled_lines)

            point_dialogue = (
                f"Dialogue: 1,{format_ass_time(global_start_time)},"
                f"{format_ass_time(end_t)},BodyStyle,,0,0,0,,{final_text}"
            )
            dialogues.append(point_dialogue)

            global_start_time = end_t

        # --- 3. Write File ---
        with open(Config.FILES["SUBTITLES"], "w", encoding="utf-8") as f:
            f.write(header_ass + "\n")
            f.write("\n".join(dialogues))

        print(f"✅ Word-styled subtitles saved to: {Config.FILES['SUBTITLES']}")
        return Config.FILES["SUBTITLES"]


    # ... (render method remains the same) ...
    def render(self, audio_paths):
        """
        Renders the final video using the merged audio and the generated subtitles.
        """
        if not audio_paths:
            print("❌ Cannot render: No audio paths provided.")
            return

        print("🎬 Rendering Final Video...")
        
        # --- Step 1: Merge Audio Chunks ---
        merged_audio_path = Config.FILES["AUDIO_MERGED"]
        if not self._merge_audio(audio_paths, merged_audio_path):
            return 

        image_path = Config.FILES["IMAGE_CLEAN"]
        ass_path = Config.FILES["SUBTITLES"]
        safe_ass = ass_path.replace("\\", "/").replace(":", "\\:")

        # --- Step 2: Set FFmpeg Command ---
        filters = (
            "zoompan=z='min(zoom+0.0015,1.5)':d=1500:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=512x912,"
            "eq=brightness=-0.4,"
            f"ass='{safe_ass}'" 
        )

        cmd = [
            'ffmpeg', '-y', '-loop', '1',
            '-i', image_path, 
            '-i', merged_audio_path,
            '-vf', filters,
            '-c:v', 'libx264', 
            '-pix_fmt', 'yuv420p',
            '-shortest', Config.FILES["VIDEO_FINAL"]
        ]

        # --- Step 3: Run FFmpeg ---
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            print(f"🎉 SUCCESS! Video saved: {Config.FILES['VIDEO_FINAL']}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Render Failed. FFmpeg Code: {e.returncode}. Check FFmpeg output or permissions.")
        except FileNotFoundError:
            print("❌ Render Failed: FFmpeg command not found. Ensure FFmpeg is installed and in your PATH.")
        finally:
            if os.path.exists(merged_audio_path):
                os.remove(merged_audio_path)