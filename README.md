# video-Zebra-china

Codex skill and standalone scripts for turning YouTube or local foreign-language videos into:

- Simplified Chinese subtitles
- Mandarin dubbing
- final MP4 exports with burned-in subtitles

The current pipeline uses:

- `yt-dlp` for YouTube download
- sibling English `.srt` files or transcript JSON for local video inputs
- `faster-whisper` for YouTube or fallback local ASR
- Volcengine `TranslateText` for subtitle translation
- Volc TTS with API-key mode first: `VOLCENGINE_TTS_API_KEY` + `VOLCENGINE_TTS_RESOURCE_ID` + `VOLCENGINE_TTS_URL`
- legacy TTS auth remains as a fallback when only `VOLCENGINE_TTS_APP_ID` + `VOLCENGINE_TTS_ACCESS_KEY` are available
- `ffmpeg` for audio mixing and final export

## Repository Layout

- `SKILL.md`: Codex skill entry
- `scripts/localize_video.py`: end-to-end pipeline
- `scripts/run_localize_video.sh`: launcher that prefers `.venv` and falls back to `python3`
- `scripts/run_localize_video.ps1`: Windows PowerShell launcher
- `references/runtime-requirements.md`: setup notes and troubleshooting
- `agents/openai.yaml`: skill metadata

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install runtime tools:

```text
Required for all modes: ffmpeg, ffprobe
Required only for YouTube inputs: yt-dlp
Required only for ASR fallback: faster-whisper
```

Set credentials for translation + dubbing:

```powershell
$env:VOLCENGINE_ACCESS_KEY="AK..."
$env:VOLCENGINE_SECRET_KEY="SK..."
$env:VOLCENGINE_REGION="cn-north-1"
$env:VOLCENGINE_TTS_API_KEY="your-ark-api-key"
$env:VOLCENGINE_TTS_RESOURCE_ID="your-tts-resource-id"
$env:VOLCENGINE_TTS_URL="https://your-tts-endpoint"
```

For the current local course workflow, output the localized lessons under:

`C:\Users\陈序谦\Desktop\next.js`

This repository is already a usable Codex skill source because it includes `SKILL.md` and `agents/openai.yaml`. Pushing to GitHub is useful for backup and reuse, but not required for the skill to work locally.

## Usage Modes

### 1. Local video + sibling English SRT

Recommended for downloaded courses that already include `*_en.srt` next to the video.

```powershell
.\scripts\run_localize_video.ps1 `
  --input "C:\path\to\lesson.mp4" `
  --workdir "C:\Users\陈序谦\Desktop\next.js\lesson-local" `
  --mute-original-audio
```

If the subtitle is not named `lesson_en.srt`, pass it explicitly:

```powershell
.\scripts\run_localize_video.ps1 `
  --input "C:\path\to\lesson.mp4" `
  --input-srt "C:\path\to\custom-lesson.srt" `
  --workdir "C:\Users\陈序谦\Desktop\next.js\lesson-local" `
  --mute-original-audio
```

This mode does not need `yt-dlp` or `faster-whisper`.

### 2. Local video + transcript JSON

Use this when you already have timestamped transcript JSON in the format documented in `references/runtime-requirements.md`.

```powershell
.\scripts\run_localize_video.ps1 `
  --input "C:\path\to\lesson.mp4" `
  --transcript-json "C:\path\to\segments.json" `
  --workdir "C:\Users\陈序谦\Desktop\next.js\lesson-json" `
  --mute-original-audio
```

### 3. YouTube URL

The legacy YouTube path still works.

```bash
scripts/run_localize_video.sh \
  --input "https://www.youtube.com/watch?v=..." \
  --workdir ./runs/demo
```

If YouTube blocks anonymous download, reuse browser cookies:

```bash
scripts/run_localize_video.sh \
  --input "https://www.youtube.com/watch?v=..." \
  --workdir ./runs/demo \
  --cookies-from-browser edge
```

## Outputs

The pipeline writes these files into the selected work directory:

- `source.*`
- `audio.wav`
- `transcript.json`
- `translated_segments.json`
- `subtitles.zh.srt`
- `dub_track.wav`
- `final_audio.wav`
- `final.mp4`

When `--mute-original-audio` is enabled, `final_audio.wav` contains only the synthesized Chinese dubbing.
