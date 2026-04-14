# video-Zebra-china

Codex skill and local scripts for turning an entire course directory or a single foreign-language video into:

- Simplified Chinese subtitles
- Mandarin male dubbing
- final MP4 exports

The default workflow on this machine is course-directory batch processing.

## Repository Layout

- `SKILL.md`: root skill entry, now course-directory first
- `scripts/localize_course.py`: course-level batch orchestration
- `scripts/run_localize_course.ps1`: Windows course wrapper
- `scripts/localize_video.py`: single-lesson engine
- `scripts/run_localize_video.ps1`: Windows single-lesson wrapper
- `references/runtime-requirements.md`: setup and credential notes
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
$env:VOLCENGINE_TTS_API_KEY="your-api-key"
$env:VOLCENGINE_TTS_RESOURCE_ID="3282640873"
$env:VOLCENGINE_TTS_URL="https://openspeech.bytedance.com/api/v1/tts"
$env:VOLCENGINE_TTS_CLUSTER="volcano_tts"
```

Default output root:

`C:\Users\陈序谦\Desktop\next.js`

## Primary Workflow: Course Directory

Use this when a course folder contains lesson `mp4` files plus sibling English subtitles named `*_en.srt`.

```powershell
.\scripts\run_localize_course.ps1 `
  --course-dir "C:\Users\陈序谦\Desktop\nextjs-react-the-complete-guide\02 -React复习"
```

Default behavior:

- output root is `C:\Users\陈序谦\Desktop\next.js`
- voice is `zh_male_liufei_uranus_bigtts`
- original audio is muted
- existing lesson outputs are overwritten

For a course like `02 -React复习`, the wrapper writes:

- final lesson videos directly to `C:\Users\陈序谦\Desktop\next.js\02 -React复习`
- intermediate files to `C:\Users\陈序谦\Desktop\next.js\02 -React复习\_work\<lesson-stem>`
- batch summary to `C:\Users\陈序谦\Desktop\next.js\02 -React复习\batch-localize.summary.json`

## Secondary Workflow: Single Lesson

Use this for debugging or rerunning one lesson.

```powershell
.\scripts\run_localize_video.ps1 `
  --input "C:\path\to\lesson.mp4" `
  --workdir "C:\Users\陈序谦\Desktop\next.js\lesson-workdir" `
  --mute-original-audio `
  --voice "zh_male_liufei_uranus_bigtts"
```

## Outputs

Course wrapper output:

- same-named localized lesson `.mp4` files in the course output directory
- `_work\<lesson-stem>\subtitles.zh.srt`
- `_work\<lesson-stem>\dub_track.wav`
- `_work\<lesson-stem>\final_audio.wav`
- `_work\<lesson-stem>\stdout.log`
- `_work\<lesson-stem>\stderr.log`
- `batch-localize.summary.json`

Single-lesson engine output:

- `source.*`
- `transcript.json`
- `translated_segments.json`
- `subtitles.zh.srt`
- `dub_track.wav`
- `final_audio.wav`
- `final.mp4`
