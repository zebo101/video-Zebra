# Runtime Requirements

## Required Tools

- `ffmpeg`
- `ffprobe`

## Optional Tools

- `yt-dlp`: only for YouTube inputs
- `faster-whisper`: only when no sibling English subtitle or transcript JSON exists

## Preferred Windows Entry Points

Course directory:

```powershell
.\scripts\run_localize_course.ps1 `
  --course-dir "C:\path\to\course"
```

Single lesson:

```powershell
.\scripts\run_localize_video.ps1 `
  --input "C:\path\to\lesson.mp4" `
  --workdir "C:\path\to\lesson-workdir"
```

## Environment Variables

- `VOLCENGINE_ACCESS_KEY`: required for Volcengine `TranslateText`
- `VOLCENGINE_SECRET_KEY`: required for Volcengine `TranslateText`
- `VOLCENGINE_REGION`: translation region, defaults to `cn-north-1`
- `VOLCENGINE_TTS_API_KEY`: required for API-key TTS mode
- `VOLCENGINE_TTS_RESOURCE_ID`: use `3282640873` for the current speech app
- `VOLCENGINE_TTS_URL`: use `https://openspeech.bytedance.com/api/v1/tts`
- `VOLCENGINE_TTS_CLUSTER`: use `volcano_tts`

Legacy `VOLCENGINE_TTS_APP_ID` + `VOLCENGINE_TTS_ACCESS_KEY` remains only as a fallback for the older single-lesson path.

## Default Course Workflow

For local course directories that already include `lesson.mp4` plus `lesson_en.srt`, this skill prefers the subtitle file instead of re-running ASR.

Default assumptions:

- output root is `C:\Users\陈序谦\Desktop\next.js`
- voice is `zh_male_liufei_uranus_bigtts`
- original audio is muted
- lesson outputs are overwritten on rerun

Course wrapper output structure:

- `C:\Users\陈序谦\Desktop\next.js\<course-name>\<lesson-name>.mp4`
- `C:\Users\陈序谦\Desktop\next.js\<course-name>\_work\<lesson-stem>\...`
- `C:\Users\陈序谦\Desktop\next.js\<course-name>\batch-localize.summary.json`

## Transcript JSON Shape

The single-lesson engine accepts either:

1. A raw array of segment objects
2. An object with a top-level `segments` array

Each segment should look like:

```json
{
  "start": 0.0,
  "end": 2.4,
  "text": "Original speech",
  "translated_text": "中文字幕，可选"
}
```

If `translated_text` is present for every segment, the script skips Volcengine text translation and goes straight to subtitle rendering and TTS.

## Common Failure Modes

### Missing sibling `*_en.srt` for a lesson

The course wrapper marks that lesson as failed in `batch-localize.summary.json` and continues with the rest of the course.

### Missing `VOLCENGINE_ACCESS_KEY` or `VOLCENGINE_SECRET_KEY`

Provide pre-translated `translated_text` in transcript JSON, or stop after subtitle extraction and translate elsewhere before rerunning.

### Missing `VOLCENGINE_TTS_API_KEY`

Run with `--skip-tts` through the single-lesson engine for subtitles only, or configure the speech app credentials first.

### Missing `VOLCENGINE_TTS_RESOURCE_ID` or `VOLCENGINE_TTS_URL`

Configure both before using API-key dubbing. The current preferred values for this machine are `3282640873` and `https://openspeech.bytedance.com/api/v1/tts`.

### Invalid Speaker

If the API returns a speaker error, switch `--voice` to another enabled speaker in the same speech application.

### Output Root Equals Source Course Directory

Do not point `--output-root` to the source course directory. The course wrapper blocks this to avoid overwriting source videos in place.
