# APEX Shortz — Unified Workspace (Archive)

Monorepo archive of the local AI short-video generation experiments that led to [apex-ai-shortz](https://github.com/mrankitpanicker/apex-ai-shortz), the current maintained pipeline. Everything here runs on local hardware: text generation → TTS narration → subtitle alignment → FFmpeg render.

## Repository layout

| Directory | What it is |
|---|---|
| `Shortz/` | Desktop app version of the Shortz pipeline — GUI (`gui.py`), PyInstaller spec (`ShortzApp.spec`), system design notes, per-Python-version requirements files |
| `Psycho/` | Psychology-facts shorts generator — `src/` pipeline (text → image → audio → video) driven by prompt files in `input/` |
| `Rashi/` | Astrology (`Astro/`) and devotional (`Dharmik/`) video pipelines — also published standalone as [rashi-astrology-bot](https://github.com/mrankitpanicker/rashi-astrology-bot) |
| `gemini/` | Gemini-based variant of the puzzle/facts generator with its own `src/` pipeline |
| `cmnd/` | FFmpeg and ASS-subtitle command experiments and helper scripts |
| `font/` | Hindi font used for subtitle rendering |

## Status

**Historical archive** — kept as the record of how the pipeline evolved. For the production version with the FastAPI API server, Redis queue, Docker Compose setup, and monitoring dashboard, see [apex-ai-shortz](https://github.com/mrankitpanicker/apex-ai-shortz).

## Dev environment

- **OS:** Windows / WSL2 (Ubuntu)
- **Hardware:** Ryzen 7 · RTX 3050 (Mobile)
- **Primary tools:** Python, Docker, Redis, FastAPI
