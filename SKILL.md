---
name: youtube-chinese-localizer
description: Use when Codex needs to batch-convert a course directory or local foreign-language video into Simplified Chinese subtitles, Mandarin dubbing, and final MP4 exports; also use for requests about 整套课程、课程目录、批量课时、中文语境配音、中文字幕、中文配音、导出成片.
---

# Course Chinese Localizer

## Overview

Turn an entire course directory or a single local video into Chinese-localized deliverables:

- concise Simplified Chinese subtitles
- Mandarin male dubbing
- final MP4 outputs ready to review

Prefer the course-level wrapper first. Single-video processing remains available for debugging and one-off reruns.

## Workflow

1. Confirm the input.

Prefer these input shapes in order:

- a local course directory containing `*.mp4`
- a single local video file
- a transcript JSON when timestamps already exist

2. Check runtime prerequisites.

Read [references/runtime-requirements.md](references/runtime-requirements.md) before first use or whenever tools or credentials may be missing.

3. Run the correct wrapper.

For a course directory, use:

```powershell
.\scripts\run_localize_course.ps1 `
  --course-dir "C:\path\to\course"
```

For a single lesson, use:

```powershell
.\scripts\run_localize_video.ps1 `
  --input "C:\path\to\lesson.mp4" `
  --workdir "C:\Users\陈序谦\Desktop\next.js\lesson"
```

4. Verify outputs.

For course directories, expect:

- final lesson videos directly under the course output directory with the original lesson filenames
- `_work\<lesson-stem>\...` containing subtitles, dub track, logs, and other intermediate files
- `batch-localize.summary.json` recording per-lesson status

For single lessons, expect:

- `subtitles.zh.srt`
- `dub_track.wav`
- `final_audio.wav`
- `final.mp4`

## Decision Rules

1. If the user gives a course directory, use `run_localize_course.ps1` first.
2. Default output root is `C:\Users\陈序谦\Desktop\next.js`.
3. Default dubbing voice is `zh_male_liufei_uranus_bigtts`.
4. Default export is Chinese dubbing only, with original audio muted.
5. Prefer Volcengine API-key TTS with:
   `VOLCENGINE_TTS_API_KEY`, `VOLCENGINE_TTS_RESOURCE_ID`, `VOLCENGINE_TTS_URL`, `VOLCENGINE_TTS_CLUSTER`
6. For local course folders, prefer sibling `*_en.srt` subtitles instead of re-running ASR.

## Failure Handling

- If a lesson is missing its sibling `*_en.srt`, mark that lesson as failed and continue with the rest of the course.
- If TTS credentials are missing, stop before dubbing instead of guessing.
- If subtitle burn-in fails, keep the subtitle file and lesson work directory for inspection.
- If rerunning a course, the course wrapper overwrites the target lesson output and its `_work` directory by default.

## Resources

- [scripts/run_localize_course.ps1](scripts/run_localize_course.ps1): primary Windows wrapper for course directories
- [scripts/localize_course.py](scripts/localize_course.py): course-level batch orchestration
- [scripts/run_localize_video.ps1](scripts/run_localize_video.ps1): single-lesson wrapper for reruns and debugging
- [scripts/localize_video.py](scripts/localize_video.py): single-lesson translation, TTS, mix, and export engine
- [references/runtime-requirements.md](references/runtime-requirements.md): environment variables, runtime tools, and troubleshooting
