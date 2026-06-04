import os
import subprocess
import sys
import math
import random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGraphicsDropShadowEffect,
    QSizePolicy,QScrollArea
)
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QLinearGradient, QPen
from PyQt6.QtCore import Qt, QRectF, QTimer, QCoreApplication
from PyQt6.QtWidgets import QMessageBox

# ====================================================================
# 1. ⚙️ CONFIGURATION SECTION (RGBA/HEX COLORS & STYLES)
# ====================================================================

class Config:
    # --- Base Colors (HEX) ---
    BACKGROUND_DARK = "#050510"  
    TEXT_DARK = "#001016"       
    TEXT_LIGHT_DEFAULT = "#E6F0FF"
    TEXT_LIGHT_LOG = "#D2DAFA"  
    TEXT_WHITE = "#FFFFFF"

    # --- Dropdown/Menu Colors ---
    DROPDOWN_BG_DARK = "#0D1225" 
    DROPDOWN_BORDER_NEON = "#00BFFF" 
    
    # --- Metrics Box Background (Styling applied to the group container) ---
    METRICS_BG = "rgba(10, 15, 30, 180)" # Dark, highly translucent background
    METRICS_BORDER = "rgba(100, 100, 100, 50)" # Subtle border
    METRICS_PADDING = "8px 10px" # Internal padding for the box

    # --- Start Button Gradient (Blue/Cyan) ---
    GRAD_START_STOP0 = "rgba(0, 180, 255, 255)"
    GRAD_START_STOP1 = "rgba(0, 255, 255, 255)"
    
    # --- Chip Gradient (Blue/Magenta) ---
    GRAD_CHIP_STOP0 = "rgba(0, 180, 255, 255)"
    GRAD_CHIP_STOP1 = "rgba(255, 0, 255, 255)"
    

    # Your Neon Rainbow Colors (from previous turns)
    WAVE_COLORS = [
        QColor(0, 255, 255, 180),     # Cyan
        QColor(80, 210, 255, 180),    # Aqua Blue
        QColor(0, 255, 170, 180),     # Mint Green
        QColor(255, 255, 120, 180),   # Neon Yellow
        QColor(255, 170, 50, 180),    # Amber
        QColor(255, 90, 200, 180),    # Pink-Magenta
        QColor(180, 100, 255, 180),   # Violet
    ]

    # Ranges for randomizing wave properties
    WAVE_CYCLE_RANGE = (2.5, 4.5)  # Number of wave peaks across the widget
    WAVE_AMPLITUDE_RANGE = (0.8, 1.2) # Base height multiplier
    # Speed factors for alternating layers
    WAVE_SPEED_SLOW = 0.5
    WAVE_SPEED_FAST = 1.0

    # --- Secondary Button Border ---
    BORDER_COLOR_A = "rgba(0, 180, 255, 255)"
    BORDER_COLOR_B = "rgba(0, 255, 255, 255)"

    # --- Shadow Styles (HEX) ---
    SHADOW_NEON_COLOR = "#00DFFF"
    SHADOW_WHITE_COLOR = "#FFFFFF"

    # --- Glass/Background Colors (must use RGBA for transparency) ---
    GLASS_FILL_TOP = QColor(255, 255, 255, 50)
    GLASS_FILL_MID = QColor(255, 255, 255, 25)
    GLASS_FILL_BOT = QColor(255, 255, 255, 10)
    GLASS_BORDER = QColor(255, 255, 255, 70)
    LOG_BG = QColor(3, 7, 20, 170)
    LOG_BORDER = QColor(255, 255, 255, 40)
    
    # --- Wave Variation Parameters ---
    WAVE_CYCLE_RANGE = (2.0, 5.0)
    WAVE_AMPLITUDE_RANGE = (0.7, 1.3)
    WAVE_SPEED_FAST = 1.3
    WAVE_SPEED_SLOW = 0.7


# ====================================================================
# 2. 🌊 CORE COMPONENTS & ANIMATION
# ====================================================================

# --- Helper for applying a bright neon shadow to text ---
def apply_neon_shadow(widget, color_hex, radius=12, x_offset=0, y_offset=0):
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(radius)
    shadow.setXOffset(x_offset)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(color_hex))
    widget.setGraphicsEffect(shadow)

# --- FLUENT GLASS CARD WIDGET (Unchanged) ---
class FluentGlassCard(QWidget):
    def __init__(self, parent=None, radius=26):
        super().__init__(parent)
        self.radius = radius
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setYOffset(18)
        shadow.setColor(QColor(0, 0, 0, 230))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, Config.GLASS_FILL_TOP)
        grad.setColorAt(0.5, Config.GLASS_FILL_MID)
        grad.setColorAt(1.0, Config.GLASS_FILL_BOT)
        painter.fillPath(path, grad)
        border_pen = QPen(Config.GLASS_BORDER)
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.drawPath(path)



class AnimatedWaveProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress = 0.0
        self.wave_offset = 0.0

        # Colors from Config (use your neon RGBA here)
        self.colors = Config.WAVE_COLORS

        self.cycle_variation = [random.uniform(0.7, 1.8) for _ in self.colors]
        self.phase_offsets = [random.uniform(0, 2 * math.pi) for _ in self.colors]
        self.phase_offsets_2 = [random.uniform(0, 2 * math.pi) for _ in self.colors]  # extra wobble

        self.speed_factors = [random.uniform(0.7, 1.4) for _ in self.colors]
        self.amplitude_factors = [random.uniform(0.7, 1.4) for _ in self.colors]

        # per-wave vertical offset inside the band (some waves slightly higher/lower)
        self.vertical_offsets = [random.uniform(-0.25, 0.25) for _ in self.colors]


        # Smooth one-direction animation
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.animate_wave)
        self.anim_timer.start(16)  # ~60 FPS

    def animate_wave(self):
        """Move all waves in one direction (left → right)."""
        self.wave_offset -= 0.09
        if self.wave_offset > 6.28:  # 2π
            self.wave_offset -= 6.28
        self.update()

    def setProgress(self, progress: float):
        self.progress = max(0.0, min(100.0, progress))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        width = max(1, rect.width())
        height = rect.height()

        # All waves live only in the bottom band of the widget
        # (like your screenshot)
        # At 0%: very thin band, at 100%: thicker but still low
        base_band = height * 0.5
        extra_band = height * 0.30 * (self.progress / 100.0)
        band_height = base_band + extra_band   # total vertical space for waves

        # Baseline where the waves float
        baseline = height - band_height * 0.6

        # Draw from back → front
        for i in range(len(self.colors) - 1, -1, -1):
            color = self.colors[i]
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)

            path = QPainterPath()
            path.moveTo(0, height)

            cycles = self.cycle_variation[i]
            phase = self.phase_offsets[i]
            speed = self.speed_factors[i]
            amp_factor = self.amplitude_factors[i]


            # Per-layer horizontal offset (controls speed)
            # 1.5 = speed boost; reduce/increase to taste
            offset = self.wave_offset * (speed * 1.2)

            # Small amplitude so the shape stays natural/flat
            amplitude_px = band_height * 0.5 * amp_factor

            for x in range(width + 1):
                x_norm = x / float(width)

                wave = math.sin(
                    x_norm * 2 * math.pi * cycles +
                    self.wave_offset * speed +
                    phase
                )

                # Map [-1,1] → [-0.5,0.5] then scale
                y_top = baseline - wave * amplitude_px * 0.5

                # Clamp to stay inside bottom band
                y_top = max(height - band_height, min(baseline + amplitude_px * 0.2, y_top))

                path.lineTo(x, y_top)

            # Close shape down to bottom
            path.lineTo(width, height)
            path.lineTo(0, height)

            painter.drawPath(path)





# ====================================================================
# 3. 🏠 MAIN WINDOW (UI SETUP & LOGIC)
# ====================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AUTOMATION BY ANKIT")
        self.setFixedSize(1000, 700) 
        
        self.current_progress = 0.0
        self.is_running = False 
       
        
        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self.update_progress)
        self.simulation_timer.setInterval(50)

        # Central widget and layout setup
        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet(f"""
            QWidget#central {{
                background-image: url("gui.png");
                background-position: center;
                background-repeat: no-repeat;
                background-color: {Config.BACKGROUND_DARK};
            }}
        """)
        self.setCentralWidget(central)
        main_layout = QGridLayout(central)
        main_layout.setContentsMargins(60, 40, 60, 40)
        main_layout.setHorizontalSpacing(40)
        main_layout.setVerticalSpacing(30)
        
        # --- UI Components Setup ---

        # 1. Automation Card (R0, C0)
        automation_card = FluentGlassCard(radius=26)
        automation_card.setStyleSheet("""
            QWidget:hover {
                border: 2px solid rgba(0, 255, 255, 100);
            }
        """)
        # Use QVBoxLayout for stacking components vertically
        auto_layout = QVBoxLayout(automation_card)
        auto_layout.setContentsMargins(28, 24, 28, 24)
        auto_layout.setSpacing(18)
        
        # --- Voice Dropdown (QComboBox) - FIRST ELEMENT ---
        voice_dropdown = QComboBox()
        voice_dropdown.setFont(QFont("Segoe UI", 10))
        voice_dropdown.addItem("⚙️ Select Voice Engine")
        voice_dropdown.addItem("👤 Clone your voice")
        voice_dropdown.addItem("♂️ Male")
        voice_dropdown.addItem("♀️ Female")
        voice_dropdown.setStyleSheet(f"""
            QComboBox {{
                background-color: {Config.DROPDOWN_BG_DARK};
                color: {Config.TEXT_WHITE};
                border: 2px solid rgba(255, 255, 255, 50);
                border-radius: 14px;
                padding: 10px 12px;
            }}
            QComboBox::drop-down {{
                border: 0px;
                width: 25px;
            }}
            QComboBox QAbstractItemView {{
                background: #0088CC;
                border: 1px solid {Config.DROPDOWN_BORDER_NEON};
                selection-background-color: #0088CC;
            }}
        """)
        voice_dropdown.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        
        # --- Start Button (Same size as Dropdown) ---
        self.start_btn = QPushButton("START AUTOMATION ▶")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.start_btn.clicked.connect(self.start_automation) 
        
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Config.GRAD_START_STOP0},
                    stop:1 {Config.GRAD_START_STOP1}
                );
                color: {Config.TEXT_DARK};
                border-radius: 20px;
                padding: 10px 10px; 
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(50, 200, 255, 255),
                    stop:1 rgba(50, 255, 255, 255)
                );
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 150, 230, 255);
            }}
        """)
        self.start_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        # --- Open Folder Button ---
        open_btn = QPushButton("📁  OUTPUT FOLDER")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setFont(QFont("Segoe UI", 10))
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border-radius: 20px;
                padding: 10px 10px;
                border: 2px solid white;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 25);
            }
        """)
        open_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        # 🔗 CONNECT THE BUTTON HERE
        open_btn.clicked.connect  #self.open_output_folder


        # Final layout for Automation Card: Stacked Vertically
        auto_layout.addStretch()
        auto_layout.addWidget(voice_dropdown) # 1. Dropdown
        auto_layout.addWidget(self.start_btn)  # 2. Start Button
        auto_layout.addWidget(open_btn)      # 3. Open Folder
        auto_layout.addStretch()


        # 2. Progress Card (R0, C1)
        progress_card = FluentGlassCard(radius=26)
        progress_card.setStyleSheet("""
            QWidget:hover {
                border: 2px solid rgba(255, 0, 255, 100);
            }
        """)
        prog_layout = QVBoxLayout(progress_card)
        prog_layout.setContentsMargins(28, 24, 28, 24)
        prog_layout.setSpacing(14)

        # Title/Percentage Labels
        self.title = QLabel("TOTAL PROGRESS")
        self.title.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.title.setStyleSheet(f"color: {Config.TEXT_LIGHT_DEFAULT};")
        apply_neon_shadow(self.title, Config.SHADOW_NEON_COLOR, radius=8)

        percent_row = QHBoxLayout()
        
        # PERCENTAGE LABEL WITH SELF-SHADOW 
        self.percent_label = QLabel("0%") 
        self.percent_label.setFont(QFont("Segoe UI", 40, QFont.Weight.Bold))
        self.percent_label.setStyleSheet(f"color: {Config.TEXT_WHITE};")
        apply_neon_shadow(self.percent_label, Config.SHADOW_WHITE_COLOR, radius=3) 

        # Chip (GOLDEN POWER CELL ⚡)
        chip = QLabel("PRO")
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        chip.setFixedHeight(28)

        chip.setStyleSheet("""
            QLabel {
                padding: 4px 18px;
                border-radius: 14px;

                /* Golden energy bar */
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0   #7A5A00,
                    stop:0.20 #BA8B00,
                    stop:0.50 #FFD93D,
                    stop:0.80 #FFE55E,
                    stop:1.0 #FFF6AE
                );

                /* Bright edge like a charged cell */
                border: 1px solid #FFE55E;

                /* Electric text */
                color: #1A1200;
                letter-spacing: 0.6px;
            }
        """)



        percent_row.addWidget(self.percent_label)
        percent_row.addStretch()
        percent_row.addWidget(chip)


        # WAVEFORM AREA 
        self.waveform_widget = AnimatedWaveProgress(self)
        self.waveform_widget.setFixedHeight(80)
        self.waveform_widget.setStyleSheet(f"""
            QWidget {{
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 60);
                background-color: rgba(6, 10, 30, 120);
            }}
        """)
        
        # Metrics setup
        metrics_title = QLabel("SESSION METRICS")
        metrics_title.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        metrics_title.setStyleSheet(f"color: {Config.TEXT_LIGHT_DEFAULT};")
        
        # Metrics HTML content updated for requested data and spacing
        metrics_html_content = (
            f"Process ID:  PRO TIER <br><br>"
            f"Engine:   Text To Voice <br><br>"
            f"Renderer:   Video Generator  <br><br>"
            f"Status:   Idle  "
        )
        self.metrics_body = QLabel(metrics_html_content)
        self.metrics_body.setFont(QFont("Consolas", 9))
        
        # Metrics Grouping Widget (Styled Box)
        metrics_group_widget = QWidget()
        metrics_group_layout = QVBoxLayout(metrics_group_widget)
        metrics_group_layout.setContentsMargins(10, 10, 10, 10)
        metrics_group_layout.addWidget(metrics_title)
        metrics_group_layout.addWidget(self.metrics_body)

        # Apply dark styling to the whole metrics group widget
        metrics_group_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {Config.METRICS_BG};
                border: 1px solid {Config.METRICS_BORDER};
                border-radius: 10px;
            }}
            /* Ensure the text inside retains its color */
            QLabel {{
                color: {Config.TEXT_LIGHT_LOG};
                background: transparent;
                border: none;
                padding: 0;
            }}
        """)
        
        self.metrics_body.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)


        prog_layout.addWidget(self.title)
        prog_layout.addLayout(percent_row)
        prog_layout.addSpacing(8)
        prog_layout.addWidget(self.waveform_widget) 
        prog_layout.addSpacing(10)
        prog_layout.addWidget(metrics_group_widget) 


        # 3. Log Card (R1, C0, span 2)
        log_card = FluentGlassCard(radius=26)
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(24, 20, 24, 20)
        log_layout.setSpacing(10)

        log_title = QLabel("SYSTEM LOG")
        log_title.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        log_title.setStyleSheet(f"color: {Config.TEXT_LIGHT_DEFAULT};")
        apply_neon_shadow(log_title, Config.SHADOW_WHITE_COLOR, radius=6)

        # 1. Define the QLabel content (self.log_box)
        self.log_box = QLabel(
            "[12:00:00] System ready. Press START to begin."
        )
        self.log_box.setFont(QFont("Consolas", 9))
        self.log_box.setWordWrap(True) # Ensure text wraps
        self.log_box.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding 
        )
        self.log_box.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # 2. Create the QScrollArea wrapper
        log_scroll_area = QScrollArea()
        log_scroll_area.setWidgetResizable(True)
        log_scroll_area.setWidget(self.log_box)

        # 3. Apply Styling to the QScrollArea and its contents
        log_scroll_area.setStyleSheet(f"""
            /* Style the Scroll Area background/border */
            QScrollArea {{
                background-color: rgba(3, 7, 20, 170); /* LOG_BG color */
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 40); /* LOG_BORDER color */
            }}
            /* Ensure the inner QLabel content (text) is correctly colored and padded */
            QLabel {{ 
                color: {Config.TEXT_LIGHT_LOG};
                background: transparent;
                padding: 8px 10px; 
            }}
            /* Style the scrollbar itself for the dark theme */
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 8px; /* Small scrollbar */
            }}
            QScrollBar::handle:vertical {{
                /* Use a bright, contrasting color for the handle */
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 255, 255, 200), /* Cyan Neon */
                    stop:1 rgba(0, 100, 255, 200)  /* Blue Neon */
                );
                border: 1px solid rgba(0, 255, 255, 150); /* Subtle neon border */
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """)

        # 4. Update Layout to use the Scroll Area
        log_layout.addWidget(log_title)
        log_layout.addWidget(log_scroll_area)

        # Place cards in grid (Log Card is wide)
        main_layout.addWidget(automation_card, 0, 0, 1, 1)
        main_layout.addWidget(progress_card,    0, 1, 1, 1)
        main_layout.addWidget(log_card,         1, 0, 1, 2)

        # 🔥 Trigger auto mode check after UI fully builds
        QTimer.singleShot(0, self.check_auto_mode)


    
    def start_automation(self):
        """Starts/stops the process and controls the timer."""
        if not self.is_running:
            self.is_running = True
            self.current_progress = 0.0
            self.start_btn.setText("STOP AUTOMATION ⏹")
            # Update metrics status
            self.metrics_body.setText(self.metrics_body.text().replace("Status: **Idle**", "Status: **Encoding segments…**"))
            self.log_box.setText("[12:02:11] Session started...\n")
            self.simulation_timer.start()

        else:
            self.is_running = False
            self.start_btn.setText("START AUTOMATION ▶")
            self.metrics_body.setText(self.metrics_body.text().replace("Status: **Encoding segments…**", "Status: **Paused**"))
            self.log_box.setText(self.log_box.text() + f"\n[{QTimer.QTime.currentTime().toString('hh:mm:ss')}] Session paused by user.")
            self.simulation_timer.stop()


    def auto_trigger(self):
        if "--auto" in sys.argv:
            print("AUTO MODE TRIGGERED")
            self.start_btn.click()



    def check_auto_mode(self):
        if "--auto" in sys.argv:
            # Wait 2.5 seconds for UI to fully render
            QTimer.singleShot(2500, self.start_btn.click)




    def update_progress(self):
        """Updates progress, animation, and labels."""
        print("update_progress running:", self.current_progress)

        # Increment progress
        if self.simulation_timer.isActive():

            self.current_progress += 0.2

        # Clamp to 100
        if self.current_progress >= 99.8:
            print("FORCED COMPLETION TRIGGER")

            self.current_progress = 100.0
            self.simulation_timer.stop()
            self.is_running = False

            self.start_btn.setText("RESTART AUTOMATION ↺")

            try:
                os.makedirs(r"C:\automation\done", exist_ok=True)
                with open(r"C:\automation\done\shortz.done", "w") as f:
                    f.write("DONE")
                print("DONE FILE CREATED")
            except Exception as e:
                print("ERROR WRITING DONE FILE:", e)


        # Update waveform animation
        self.waveform_widget.setProgress(self.current_progress)

        # Update percentage label
        self.percent_label.setText(f"{int(self.current_progress)}%")

        # Log checkpoint at 50%
        if 49.9 < self.current_progress < 50.1:
            self.log_box.setText(
                self.log_box.text() + "\n[12:02:41] Encoding segments: 50% checkpoint."
            )

        if self.current_progress >= 99.8:
            print("HIT COMPLETION THRESHOLD")



# ====================================================================
# 4. 🚀 ENTRY POINT
# ====================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    if "--auto" in sys.argv:
        # Wait until window is fully shown
        def delayed_start():
            if window.isVisible():
                window.start_automation()

        QTimer.singleShot(2500, delayed_start)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()