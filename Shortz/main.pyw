# main.pyw - FINAL FIX (IMPORT METHOD)

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget, QPushButton
from PyQt6.QtCore import QCoreApplication, QObject, QTimer, Qt, QTime, QThread, pyqtSignal
from pathlib import Path

# Set up logging early
logging.getLogger().setLevel(logging.ERROR)
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "true"

# 1. SETUP PATH
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

PROJECT_ROOT = Path(CURRENT_DIR).parent 

# ====================================================================
# 2. LOGGING REDIRECTOR (Captures print() from Shortz.py)
# ====================================================================
class StreamRedirector(QObject):
    """Captures text written to sys.stdout and sends it to the GUI."""
    text_written = pyqtSignal(str)

    def write(self, text):
        self.text_written.emit(str(text))

    def flush(self):
        pass

# ====================================================================
# 3. WORKER THREAD (Direct Execution of Shortz.py)
# ====================================================================

class EngineWorker(QThread):
    log_update = pyqtSignal(str)
    status_update = pyqtSignal(float, str)
    process_finished = pyqtSignal(float, str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_requested = False
        self.current_progress = 0.0

    def run(self):
        # 1. Redirect stdout so we can see print() statements in the GUI
        original_stdout = sys.stdout
        redirector = StreamRedirector()
        redirector.text_written.connect(self._handle_stdout)
        sys.stdout = redirector

        try:
            # 2. IMPORT SHORTZ HERE (Inside the thread to avoid freezing UI on startup)
            import Shortz
            
            # 3. RUN THE AUTOMATION 
            # We call the main function directly. 
            Shortz.main_generate()
            
            self.process_finished.emit(100.0, "Generation Complete")

        except Exception as e:
            # Catch crashes and show them
            self.log_update.emit(f"FATAL ERROR: {e}")
            self.process_finished.emit(0.0, "Error: Script Failed")
        finally:
            # 4. Restore normal stdout
            sys.stdout = original_stdout

    def _handle_stdout(self, line):
        # This function processes every line printed by Shortz.py
        if not line: return
        
        # Clean up the line
        line = line.strip()
        if not line: return

        self.log_update.emit(line)
        self._check_status_update(line)

    def _check_status_update(self, line):
        import re
        status_text = ""
        progress_change = False
        
        # Status Map
        status_map = {
            "Voice Model Online": 10.0,
            "Reading Today’s Script": 20.0,
            "Synthesizing Speech Segments": 35.0,
            "Merging Audio Layers": 50.0,
            "Synchronizing Word Timeline": 65.0,
            "Crafting Dynamic Highlights": 80.0,
            "Rendering Final Sequence": 90.0,
            "Generation Complete": 100.0,
        }

        # Check milestones
        for marker, progress in status_map.items():
            if marker in line:
                self.current_progress = progress 
                status_text = marker
                progress_change = True

        # Parse Progress Bars (e.g. [███] 50%)
        match = re.search(r'\[.+\]\s*(\d+)%', line)
        if match:
            local_percent = float(match.group(1))
            
            if "Synthesizing" in line:
                # Scale 0-100 to global 20-35
                scaled = 20.0 + (local_percent * 0.15) 
                self.current_progress = max(self.current_progress, scaled)
                status_text = "Synthesizing Voices..."
                progress_change = True
            elif "Finalizing" in line or "Merging" in line:
                # Scale 0-100 to global 35-50
                scaled = 35.0 + (local_percent * 0.15)
                self.current_progress = max(self.current_progress, scaled)
                status_text = "Merging Audio Layers..."
                progress_change = True

        if progress_change:
            self.status_update.emit(self.current_progress, status_text or "Running...")

    def stop_process(self):
        self._stop_requested = True
        # Since we are running a function, we can't force kill it easily without
        # adding checks inside Shortz.py, but this ensures the UI resets.
        self.terminate()

# ====================================================================
# 4. CONTROLLER CORE
# ====================================================================

class MainController(QObject):
    
    def __init__(self, app: QApplication, window: QWidget):
        super().__init__()
        self.app = app
        self.window = window 
        self.is_running = False
        self.engine_loaded = False
        self.worker_thread = None

        self.CURRENT_DIR = CURRENT_DIR
        
        # Setup Window
        if hasattr(window, 'timer'): window.timer.stop() 
        window.is_running = False 
        
        self.initial_loader_timer = QTimer(self)
        
        buttons = window.findChildren(QPushButton)
        self.start_btn = next((b for b in buttons if "START" in b.text()), None)
        self.open_btn = next((b for b in buttons if "OUTPUT FOLDER" in b.text()), None)

        self._direct_log("System ready. Initiating engine startup simulation...")
        self._direct_update_status("Initializing", "Wait...", False, True)
        self.handle_initial_load()
        
        if self.start_btn:
            try: self.start_btn.clicked.disconnect()
            except: pass
            self.start_btn.clicked.connect(self.handle_start_automation)
            
        if self.open_btn:
            try: self.open_btn.clicked.disconnect()
            except: pass
            self.open_btn.clicked.connect(self.handle_open_output)

    def _direct_log(self, message: str):
        if not hasattr(self.window, 'log_box'): return
        current_text = self.window.log_box.text()
        # Simple buffer to prevent log from getting too huge
        lines = (current_text + f"\n[{QTime.currentTime().toString('hh:mm:ss')}] {message}").split('\n')
        if len(lines) > 30: lines = lines[-30:]
        self.window.log_box.setText('\n'.join(lines))
        # Auto-scroll to bottom
        sb = self.window.findChild(QWidget, "log_scroll_area").verticalScrollBar() if hasattr(self.window, "log_scroll_area") else None
        if sb: sb.setValue(sb.maximum())

    def _direct_update_status(self, metric_status: str, button_text: str, button_enabled: bool, chip_visible: bool):
        if not hasattr(self.window, 'metrics_body'): return
        
        metrics_html_content = (
            f"Process ID: PRO TIER \n\n"
            f"Engine: Text To Voice \n\n"
            f"Renderer: Video Generator \n\n"
            f"Status: {metric_status}"
        )
        self.window.metrics_body.setText(metrics_html_content)
        
        if self.start_btn:
            self.start_btn.setText(button_text)
            self.start_btn.setEnabled(button_enabled)
        
        if hasattr(self.window, 'voice_dropdown'): 
            self.window.voice_dropdown.setEnabled(not button_enabled) 
        if self.open_btn: 
            self.open_btn.setEnabled(button_enabled or 'COMPLETE' in metric_status.upper()) 

        if chip_visible and hasattr(self.window, 'chip'):
            self.window.chip.setText(metric_status.upper()[:10])
            self.window.chip.setStyleSheet("""
                QLabel {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00BFFF, stop:1 #FF00FF);
                    color: #001016; padding: 6px 12px; border-radius: 14px;
                }
            """)
        elif hasattr(self.window, 'chip'):
            self.window.chip.setText("IDLE")
            self.window.chip.setStyleSheet("background-color: #333; color: #E6F0FF; padding: 6px 12px; border-radius: 14px;")

    def _direct_update_progress(self, progress: float):
        if not hasattr(self.window, 'percent_label'): return
        self.window.percent_label.setText(f"{int(progress)}%")
        self.window.waveform_widget.setProgress(progress)
       
    def handle_initial_load(self):
        self.initial_loader_timer.timeout.connect(self._initial_load_finished)
        self.initial_loader_timer.start(2000) 
        
    def _initial_load_finished(self):
        self.initial_loader_timer.stop()
        self.engine_loaded = True
        self._direct_update_status("Engine Ready", "START AUTOMATION  ▶", True, False)
        self._direct_update_progress(0.0)
        self._direct_log("✅ Engine initialization complete. Ready for job.")

    def handle_start_automation(self):
        if self.is_running:
            if self.worker_thread and self.worker_thread.isRunning():
                 self.worker_thread.stop_process()
            self.is_running = False
            self._direct_update_status("Stopped", "START AUTOMATION  ▶", True, False)
            self._direct_log("Session stopped by user.")
        else:
            self.is_running = True
            self.start_btn.setText("PROCESSING...")
            self.start_btn.setEnabled(False)
            if self.open_btn: self.open_btn.setDisabled(True)
            self._direct_update_progress(0.0)
            self._direct_log("Session started. Prepairing Magic...")
            
            # Use the new Import-based Worker
            self.worker_thread = EngineWorker(parent=self)
            self.worker_thread.log_update.connect(self._direct_log)
            self.worker_thread.status_update.connect(self._update_gui_status)
            self.worker_thread.process_finished.connect(self._handle_process_finished)
            self.worker_thread.start()

    def _update_gui_status(self, percentage: float, message: str):
        self._direct_update_progress(percentage)
        if percentage >= 100.0: return 
        self._direct_update_status(message, "STOP AUTOMATION ⏹", True, True)

    def _handle_process_finished(self, final_progress: float, final_status: str):
        self.is_running = False
        self._direct_update_progress(final_progress)
        
        if "Error" in final_status or final_progress < 100.0:
            self._direct_update_status("Error", "RETRY START ▶", True, False)
            self._direct_log(f"💥 {final_status}")
            QMessageBox.critical(self.window, "Error", f"Process stopped: {final_status}")
        else:
            self._direct_update_status("Generation Complete", "RESTART AUTOMATION ↺", True, False)
            self._direct_log(f"🎉 Process finished successfully.")
            QApplication.beep()
            self.complete_automation()

    def handle_open_output(self):
        # Updated to check both Dev path and Exe path logic
        if getattr(sys, 'frozen', False):
             base = os.path.dirname(sys.executable)
        else:
             base = self.CURRENT_DIR
             
        output_dir = os.path.join(base, "output", "video")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        self._direct_log(f"Opening folder: {output_dir}")
        import subprocess
        subprocess.Popen(["explorer", output_dir])


    def complete_automation(self):
        if getattr(self, "_done_written", False):
            return

        self._done_written = True

        try:
            import time
            from pathlib import Path
            import os

            # WAIT until output file stops growing
            output_dir = Path(self.CURRENT_DIR) / "output" / "video"

            latest = max(output_dir.glob("*.mp4"), key=os.path.getctime)

            size1 = -1
            while True:
                size2 = latest.stat().st_size
                if size1 == size2:
                    break
                size1 = size2
                time.sleep(2)

            # NOW create done file
            done_dir = Path("C:/automation/done")
            done_dir.mkdir(parents=True, exist_ok=True)

            with open(done_dir / "shortz.done", "w") as f:
                f.write("done")

        except Exception as e:
            with open("C:/automation/done/shortz_error.log", "a") as f:
                f.write(str(e) + "\n")


# ====================================================================
# 5. RUN APP ENTRY POINT
# ====================================================================

if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(2) 
    except: pass
    
    # IMPORT GUI DYNAMICALLY
    try:
        from gui import MainWindow 
    except ImportError:
        import tkinter as tk
        tk.Tk().withdraw()
        tk.messagebox.showerror("Error", "gui.py not found!")
        sys.exit(1)

    if not QCoreApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QCoreApplication.instance()
        
    try:
        window = MainWindow() 
    except TypeError:
        # Fallback if gui.py constructor requires args
        window = MainWindow(None, None) 

    controller = MainController(app, window)
    window.show()
    sys.exit(app.exec())