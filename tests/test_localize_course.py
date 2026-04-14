import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "localize_course.py"
SPEC = importlib.util.spec_from_file_location("localize_course", MODULE_PATH)
localize_course = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = localize_course
SPEC.loader.exec_module(localize_course)


class LocalizeCourseTests(unittest.TestCase):
    def test_discover_course_videos_sorts_mp4_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course_dir = Path(tmpdir)
            (course_dir / "002 lesson.mp4").write_bytes(b"video")
            (course_dir / "001 lesson.mp4").write_bytes(b"video")
            (course_dir / "notes.txt").write_text("ignore", encoding="utf-8")

            videos = localize_course.discover_course_videos(course_dir)

        self.assertEqual(
            ["001 lesson.mp4", "002 lesson.mp4"],
            [video.name for video in videos],
        )

    def test_parse_args_defaults_to_course_output_root_and_male_voice(self) -> None:
        args = localize_course.parse_args(
            ["--course-dir", r"C:\courses\react"]
        )

        self.assertEqual(Path(r"C:\courses\react"), args.course_dir)
        self.assertEqual(
            Path(r"C:\Users\陈序谦\Desktop\next.js"),
            args.output_root,
        )
        self.assertEqual("zh_male_liufei_uranus_bigtts", args.voice)
        self.assertTrue(args.mute_original_audio)
        self.assertTrue(args.force_overwrite)

    def test_process_course_directory_writes_same_named_final_video_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course_dir = Path(tmpdir) / "02 -React复习"
            course_dir.mkdir()
            lesson = course_dir / "002 Module Introduction.mp4"
            subtitle = course_dir / "002 Module Introduction_en.srt"
            lesson.write_bytes(b"video")
            subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
            output_root = Path(tmpdir) / "output"

            def fake_run(args: list[str], check: bool, **kwargs) -> None:
                workdir = Path(args[args.index("--workdir") + 1])
                workdir.mkdir(parents=True, exist_ok=True)
                (workdir / "subtitles.zh.srt").write_text("字幕", encoding="utf-8")
                (workdir / "dub_track.wav").write_bytes(b"dub")
                (workdir / "final_audio.wav").write_bytes(b"final-audio")
                (workdir / "final.mp4").write_bytes(b"final-video")

            with mock.patch.object(localize_course.subprocess, "run", side_effect=fake_run) as run_mock:
                summary = localize_course.process_course_directory(
                    course_dir,
                    output_root=output_root,
                    voice="zh_male_liufei_uranus_bigtts",
                    mute_original_audio=True,
                    force_overwrite=True,
                    python_executable=Path(sys.executable),
                    video_script_path=Path("scripts/localize_video.py"),
                )

            course_output = output_root / course_dir.name
            final_video = course_output / lesson.name
            workdir = course_output / "_work" / lesson.stem
            summary_path = course_output / "batch-localize.summary.json"

            self.assertEqual(1, run_mock.call_count)
            self.assertEqual("completed", summary["lessons"][0]["status"])
            self.assertTrue(final_video.exists())
            self.assertEqual(b"final-video", final_video.read_bytes())
            self.assertTrue(workdir.exists())
            self.assertTrue((workdir / "subtitles.zh.srt").exists())
            self.assertTrue(summary_path.exists())
            parsed_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual("completed", parsed_summary["lessons"][0]["status"])

    def test_process_course_directory_marks_missing_subtitle_as_failed_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course_dir = Path(tmpdir) / "course"
            course_dir.mkdir()
            missing = course_dir / "001 Missing Subtitle.mp4"
            valid = course_dir / "002 Valid Lesson.mp4"
            valid_srt = course_dir / "002 Valid Lesson_en.srt"
            missing.write_bytes(b"video")
            valid.write_bytes(b"video")
            valid_srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

            def fake_run(args: list[str], check: bool, **kwargs) -> None:
                workdir = Path(args[args.index("--workdir") + 1])
                workdir.mkdir(parents=True, exist_ok=True)
                (workdir / "final.mp4").write_bytes(b"ok")

            with mock.patch.object(localize_course.subprocess, "run", side_effect=fake_run) as run_mock:
                summary = localize_course.process_course_directory(
                    course_dir,
                    output_root=Path(tmpdir) / "out",
                    voice="zh_male_liufei_uranus_bigtts",
                    mute_original_audio=True,
                    force_overwrite=True,
                    python_executable=Path(sys.executable),
                    video_script_path=Path("scripts/localize_video.py"),
                )

            self.assertEqual(1, run_mock.call_count)
            self.assertEqual("failed", summary["lessons"][0]["status"])
            self.assertIn("_en.srt", summary["lessons"][0]["error"])
            self.assertEqual("completed", summary["lessons"][1]["status"])

    def test_process_course_directory_overwrites_existing_final_and_workdir_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            course_dir = Path(tmpdir) / "course"
            course_dir.mkdir()
            lesson = course_dir / "003 Existing Output.mp4"
            subtitle = course_dir / "003 Existing Output_en.srt"
            lesson.write_bytes(b"video")
            subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
            output_root = Path(tmpdir) / "out"
            course_output = output_root / course_dir.name
            workdir = course_output / "_work" / lesson.stem
            workdir.mkdir(parents=True)
            (workdir / "stale.txt").write_text("stale", encoding="utf-8")
            final_video = course_output / lesson.name
            final_video.parent.mkdir(parents=True, exist_ok=True)
            final_video.write_bytes(b"old-video")

            def fake_run(args: list[str], check: bool, **kwargs) -> None:
                target_workdir = Path(args[args.index("--workdir") + 1])
                self.assertFalse((target_workdir / "stale.txt").exists())
                (target_workdir / "final.mp4").write_bytes(b"new-video")

            with mock.patch.object(localize_course.subprocess, "run", side_effect=fake_run):
                summary = localize_course.process_course_directory(
                    course_dir,
                    output_root=output_root,
                    voice="zh_male_liufei_uranus_bigtts",
                    mute_original_audio=True,
                    force_overwrite=True,
                    python_executable=Path(sys.executable),
                    video_script_path=Path("scripts/localize_video.py"),
                )

            self.assertEqual("completed", summary["lessons"][0]["status"])
            self.assertEqual(b"new-video", final_video.read_bytes())


if __name__ == "__main__":
    unittest.main()
