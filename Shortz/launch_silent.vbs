' Launches the Python script using the pythonw.exe interpreter without a console window.
Set ws = CreateObject("WScript.Shell")

' Define the paths using the absolute paths confirmed in your environment
PYTHONW_EXE = "D:\tts\venv\Scripts\pythonw.exe"
MAIN_SCRIPT = "D:\tts\Shortz\main.pyw"

' The 0 in the Run command means run hidden (SW_HIDE)
ws.Run PYTHONW_EXE & " " & MAIN_SCRIPT, 0, False