@echo off
chcp 65001 >nul
set PYTHONUTF8=1

title 🎬 AI Shorts Generator

echo =======================================================
echo    🚀 STEP 1: 🧠 Text + 🔊 Audio (venv)
echo =======================================================
echo.

cd /d "D:\tts\gemini"

echo 🔧 Activating Environment...
call "D:\tts\venv\Scripts\activate.bat"

echo ▶️ Running step1.py ...
python -X utf8 step1.py

call deactivate

echo.
echo =======================================================
echo    🎨 STEP 2: 🖼️ Image + 🎬 Video (genv)
echo =======================================================
echo.

call "D:\tts\gemini\genv\Scripts\activate.bat"

echo ▶️ Running step2.py ...
python -X utf8 step2.py

echo.
echo =======================================================
echo    🎉 ALL DONE!  
echo    📂 Opening Output Folder...
echo =======================================================
echo.

:: 1. Open folder (Non-blocking)
start "" "D:\tts\gemini\output"

:: 2. Signal the Master Script IMMEDIATELY
:: SYNC CHECK: Master Script must look for 'aishorts.done'
echo DONE > "C:\automation\done\aishorts.done"
echo ✅ Signal 'aishorts.done' sent to Master Automation.

:: 3. LIVE COUNTDOWN TIMER (5 to 1)
echo.
echo 🏁 AI Shorts job completed.
set /p ="⏳ Closing window in: " <nul
for /l %%i in (5,-1,1) do (
    set /p ="%%i... " <nul
    timeout /t 1 /nobreak >nul
)

echo.
echo 👋 Goodbye!

:: Ensure environment is closed
if defined VIRTUAL_ENV call deactivate

exit /b