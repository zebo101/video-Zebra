---
name: youtube-chinese-localizer
description: Localize YouTube or other foreign-language videos into Chinese. Use when Codex needs to turn a YouTube URL or local video into Simplified Chinese subtitles, Mandarin dubbing, and a final exported video; also use for requests about 自动下载 YouTube 视频、生成中文字幕、中文配音、混音、烧录字幕、导出成片.
---

# YouTube Chinese Localizer

## Overview

Turn a YouTube URL or local video into a Chinese-localized deliverable:

- download or ingest the source video
- transcribe speech into timestamped segments
- translate lines into natural Simplified Chinese
- synthesize Mandarin dubbing
- mix the dub with optional low-volume source audio
- export a final MP4 with burned-in subtitles or a sidecar subtitle track

Prefer the bundled script for repeatable work instead of reassembling the pipeline by hand.

## Workflow

1. Confirm the input.

Accept either:

- a YouTube URL
- a local video file
- a pre-existing transcript JSON when transcription has already been done elsewhere

2. Check runtime prerequisites.

Read [references/runtime-requirements.md](references/runtime-requirements.md) before first use or whenever the environment is missing tools. At minimum, the workflow expects `ffmpeg`. For YouTube URLs it also expects `yt-dlp`. For local speech-to-text it prefers `faster-whisper`. Translation uses Volcengine `TranslateText`; dubbing uses Volcengine TTS.

3. Run the pipeline script.

Use the default command first:

```bash
scripts/run_localize_video.sh \
  --input "https://www.youtube.com/watch?v=..." \
  --workdir ./runs/demo \
  --cookies-from-browser edge
```

Useful variants:

```bash
scripts/run_localize_video.sh \
  --input /path/to/video.mp4 \
  --workdir ./runs/local-video \
  --voice zh_female_qingxin \
  --background-volume 0.12
```

```bash
scripts/run_localize_video.sh \
  --input /path/to/video.mp4 \
  --workdir ./runs/from-transcript \
  --transcript-json /path/to/segments.json \
  --skip-transcription
```

```bash
scripts/run_localize_video.sh \
  --input "https://www.youtube.com/watch?v=..." \
  --workdir ./runs/subtitles-only \
  --skip-tts
```

4. Verify the outputs.

Expect these files inside the work directory:

- `source.*`: downloaded or copied source video
- `audio.wav`: extracted mono wav for speech processing
- `transcript.json`: timestamped source segments
- `translated_segments.json`: translated segments with Chinese text
- `subtitles.zh.srt`: Simplified Chinese subtitles
- `dub_track.wav`: synthesized Chinese dub track when TTS is enabled
- `final_audio.wav`: mixed final audio
- `final.mp4`: exported video deliverable

5. Review quality before handing off.

Check:

- subtitles stay aligned with scene changes
- Chinese phrasing is concise enough for speech
- dub volume is dominant and intelligible
- the original soundtrack, if retained, does not overpower speech
- no segment overflows badly past its subtitle time slot

## Decision Rules

Prefer this order of execution:

1. Use a provided transcript JSON if it already contains timestamps.
2. Otherwise use local `faster-whisper` if available.
3. Only download with `yt-dlp` when the input is an online URL.
4. Use Volcengine translation credentials for subtitle translation and API-key TTS credentials first for dubbing. Prefer `VOLCENGINE_TTS_API_KEY` + `VOLCENGINE_TTS_RESOURCE_ID` + `VOLCENGINE_TTS_URL`.
5. If TTS is unavailable, still produce the Chinese SRT and stop there instead of guessing.

Keep the translated Chinese concise. It is better to slightly compress the spoken line than to preserve every filler word and overrun the dub timing.

## Failure Handling

- If `yt-dlp` is missing, install it or ask for a local video file.
- If YouTube blocks anonymous download, rerun with `--cookies-from-browser edge` or another installed browser.
- If `faster-whisper` is missing, install it or require `--transcript-json`.
- If Volcengine translation credentials are missing and the transcript lacks `translated_text`, stop and request either `VOLCENGINE_ACCESS_KEY` plus `VOLCENGINE_SECRET_KEY` or a pre-translated transcript.
- If API-key TTS configuration is missing, keep generating Chinese subtitles and stop before dubbing.
- If subtitle burn-in fails because of an ffmpeg path issue, keep `subtitles.zh.srt` and export without burn-in rather than losing the localized result.

## Resources

- [scripts/run_localize_video.sh](scripts/run_localize_video.sh): wrapper that runs the pipeline inside the preinstalled `.venv`
- [scripts/localize_video.py](scripts/localize_video.py): end-to-end download, ASR, translation, TTS, subtitle, mix, and export pipeline
- [references/runtime-requirements.md](references/runtime-requirements.md): dependency setup, environment variables, and troubleshooting notes

For this user's local course workflow, prefer writing outputs under:

`C:\Users\陈序谦\Desktop\next.js`
