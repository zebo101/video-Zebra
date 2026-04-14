#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_OUTPUT_ROOT = Path(r"C:\Users\陈序谦\Desktop\next.js")
DEFAULT_VOICE = "zh_male_liufei_uranus_bigtts"


def discover_course_videos(course_dir: Path) -> list[Path]:
    return sorted(
        path for path in course_dir.iterdir() if path.is_file() and path.suffix.lower() == ".mp4"
    )


def resolve_input_srt(video_path: Path) -> Path:
    return video_path.with_name(f"{video_path.stem}_en.srt")


def course_output_dir(course_dir: Path, output_root: Path) -> Path:
    return output_root / course_dir.name


def lesson_workdir(output_dir: Path, video_path: Path) -> Path:
    return output_dir / "_work" / video_path.stem


def final_video_path(output_dir: Path, video_path: Path) -> Path:
    return output_dir / video_path.name


def write_summary(summary_path: Path, summary: dict[str, object]) -> None:
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_lesson(
    video_path: Path,
    *,
    output_dir: Path,
    python_executable: Path,
    video_script_path: Path,
    voice: str,
    mute_original_audio: bool,
    force_overwrite: bool,
) -> dict[str, str]:
    workdir = lesson_workdir(output_dir, video_path)
    final_path = final_video_path(output_dir, video_path)
    input_srt = resolve_input_srt(video_path)
    if not input_srt.exists():
        return {
            "name": video_path.stem,
            "status": "failed",
            "output": str(final_path),
            "error": f"Missing sibling subtitle: {input_srt.name}",
        }

    if force_overwrite:
        if workdir.exists():
            shutil.rmtree(workdir)
        if final_path.exists():
            final_path.unlink()

    if final_path.exists():
        return {
            "name": video_path.stem,
            "status": "skipped",
            "output": str(final_path),
        }

    workdir.mkdir(parents=True, exist_ok=True)
    stdout_log = workdir / "stdout.log"
    stderr_log = workdir / "stderr.log"
    cmd = [
        str(python_executable),
        str(video_script_path),
        "--input",
        str(video_path),
        "--workdir",
        str(workdir),
        "--input-srt",
        str(input_srt),
        "--voice",
        voice,
    ]
    if mute_original_audio:
        cmd.append("--mute-original-audio")

    try:
        with stdout_log.open("w", encoding="utf-8") as stdout_handle, stderr_log.open(
            "w", encoding="utf-8"
        ) as stderr_handle:
            subprocess.run(
                cmd,
                check=True,
                stdout=stdout_handle,
                stderr=stderr_handle,
            )
    except subprocess.CalledProcessError as exc:
        return {
            "name": video_path.stem,
            "status": "failed",
            "output": str(final_path),
            "error": f"localize_video.py exited with code {exc.returncode}",
        }

    generated_final = workdir / "final.mp4"
    if not generated_final.exists():
        return {
            "name": video_path.stem,
            "status": "failed",
            "output": str(final_path),
            "error": "Expected final.mp4 was not generated",
        }

    shutil.copy2(generated_final, final_path)
    return {
        "name": video_path.stem,
        "status": "completed",
        "output": str(final_path),
    }


def process_course_directory(
    course_dir: Path,
    *,
    output_root: Path,
    voice: str,
    mute_original_audio: bool,
    force_overwrite: bool,
    python_executable: Path,
    video_script_path: Path,
) -> dict[str, object]:
    course_dir = course_dir.expanduser().resolve()
    if not course_dir.exists():
        raise SystemExit(f"Course directory does not exist: {course_dir}")
    if not course_dir.is_dir():
        raise SystemExit(f"Course path is not a directory: {course_dir}")

    output_dir = course_output_dir(course_dir, output_root.expanduser().resolve())
    if output_dir.resolve() == course_dir:
        raise SystemExit("Output root must not resolve to the source course directory")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "_work").mkdir(parents=True, exist_ok=True)

    summary = {
        "course_dir": str(course_dir),
        "output_dir": str(output_dir),
        "voice": voice,
        "lessons": [],
    }
    summary_path = output_dir / "batch-localize.summary.json"

    for video_path in discover_course_videos(course_dir):
        result = run_lesson(
            video_path,
            output_dir=output_dir,
            python_executable=python_executable,
            video_script_path=video_script_path,
            voice=voice,
            mute_original_audio=mute_original_audio,
            force_overwrite=force_overwrite,
        )
        summary["lessons"].append(result)
        write_summary(summary_path, summary)

    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-localize a course directory into Chinese subtitles and Mandarin dubbing."
    )
    parser.add_argument("--course-dir", type=Path, required=True, help="Directory containing lesson mp4 files")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root directory for localized course outputs",
    )
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Volc TTS speaker name")
    parser.add_argument(
        "--mute-original-audio",
        dest="mute_original_audio",
        action="store_true",
        default=True,
        help="Export only Chinese dubbing without mixing the original soundtrack",
    )
    parser.add_argument(
        "--keep-original-audio",
        dest="mute_original_audio",
        action="store_false",
        help="Mix original audio under the Chinese dubbing",
    )
    parser.add_argument(
        "--force-overwrite",
        dest="force_overwrite",
        action="store_true",
        default=True,
        help="Overwrite existing lesson outputs before rerunning",
    )
    parser.add_argument(
        "--skip-existing",
        dest="force_overwrite",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = process_course_directory(
        args.course_dir,
        output_root=args.output_root,
        voice=args.voice,
        mute_original_audio=args.mute_original_audio,
        force_overwrite=args.force_overwrite,
        python_executable=Path(sys.executable),
        video_script_path=Path(__file__).with_name("localize_video.py"),
    )
    print(f"course_output={summary['output_dir']}")
    print(f"summary={Path(summary['output_dir']) / 'batch-localize.summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
