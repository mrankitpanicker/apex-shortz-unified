# src/video_gen.py
import subprocess
import textwrap
from .config import Config
from .utils import format_ass_time

class VideoEditor:
    def create_subtitles(self, text, duration):
        print("📝 Creating Animated Subtitles...")
        
        # Styles: Header(Top Red), Body(Middle White)
        # Note: Header MarginV is 30 to push it slightly up
        header_ass = f"""[Script Info]
Title: Gemini Pro
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HeaderStyle,{Config.FONT_NAME},{Config.HEADER_SIZE},{Config.COLOR_RED},&H00FFFFFF,&H00FFFFFF,&H80000000,1,0,0,0,100,100,0,0,1,4,0,8,10,10,30,1
Style: BodyStyle,{Config.FONT_NAME},{Config.BODY_SIZE},{Config.COLOR_WHITE},&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,2,5,30,30,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,{format_ass_time(duration)},HeaderStyle,,0,0,0,,दिमाग लगाओ!
"""
        events = []
        
        # Stabilized Karaoke Logic
        words = text.split()
        time_per_word = (duration - 0.5) / len(words)
        current_time = 0.0

        for i in range(len(words)):
            visible_words = words[:i+1]
            raw_string = " ".join(visible_words)
            
            # ✅ FIX: Changed width to 26. 
            # This makes lines longer, so the text block is shorter and fits on screen.
            formatted_text = "\\N".join(textwrap.wrap(raw_string, width=26))
            
            start_t = current_time
            end_t = current_time + time_per_word
            if i == len(words) - 1: end_t = duration

            events.append(f"Dialogue: 0,{format_ass_time(start_t)},{format_ass_time(end_t)},BodyStyle,,0,0,0,,{formatted_text}")
            current_time += time_per_word

        with open(Config.FILES["SUBTITLES"], "w", encoding="utf-8") as f:
            f.write(header_ass + "\n".join(events))
        
        return Config.FILES["SUBTITLES"]

    def render(self):
        print("🎬 Rendering Final Video...")
        image_path = Config.FILES["IMAGE_CLEAN"]
        audio_path = Config.FILES["AUDIO_OUT"]
        ass_path = Config.FILES["SUBTITLES"]
        safe_ass = ass_path.replace("\\", "/").replace(":", "\\:")

        # Filter: Zoom + Darken + Subtitles
        filters = (
            "zoompan=z='min(zoom+0.0015,1.5)':d=1500:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=512x912,"
            "eq=brightness=-0.4,"
            f"ass='{safe_ass}'"
        )

        cmd = [
            'ffmpeg', '-y', '-loop', '1',
            '-i', image_path, '-i', audio_path,
            '-vf', filters,
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-shortest', Config.FILES["VIDEO_FINAL"]
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            print(f"🎉 SUCCESS! Video saved: {Config.FILES['VIDEO_FINAL']}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Render Failed. Code: {e.returncode}")