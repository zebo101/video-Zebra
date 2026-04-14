import importlib.util
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "localize_video.py"
SPEC = importlib.util.spec_from_file_location("localize_video", MODULE_PATH)
localize_video = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = localize_video
SPEC.loader.exec_module(localize_video)


class LocalizeVideoTests(unittest.TestCase):
    def test_build_volc_tts_request_prefers_api_key_auth(self) -> None:
        with mock.patch.dict(
            localize_video.os.environ,
            {
                "VOLCENGINE_TTS_API_KEY": "api-key-123",
                "VOLCENGINE_TTS_RESOURCE_ID": "resource-123",
                "VOLCENGINE_TTS_URL": "https://ark.example.com/api/v1/tts",
            },
            clear=True,
        ), mock.patch.object(localize_video.uuid, "uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            request = localize_video.build_volc_tts_request(
                "你好，世界",
                speaker="zh_female_cancan_mars_bigtts",
                response_format="wav",
                sample_rate=24000,
            )

        self.assertEqual(
            "api-key-123",
            request.headers["X-api-key"],
        )
        self.assertEqual(
            "resource-123",
            request.headers["X-api-resource-id"],
        )
        self.assertEqual(
            "12345678-1234-5678-1234-567812345678",
            request.headers["X-api-request-id"],
        )
        self.assertEqual("https://ark.example.com/api/v1/tts", request.full_url)
        self.assertNotIn("X-api-app-id", request.headers)
        self.assertNotIn("X-api-access-key", request.headers)
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual("你好，世界", payload["text"])
        self.assertEqual("zh_female_cancan_mars_bigtts", payload["voice_type"])
        self.assertEqual(1.0, payload["speed_ratio"])
        self.assertEqual(1.0, payload["volume_ratio"])
        self.assertEqual("wav", payload["audio_config"]["format"])
        self.assertEqual(24000, payload["audio_config"]["sample_rate"])

    def test_build_volc_tts_request_requires_url_and_resource_for_api_key(self) -> None:
        with mock.patch.dict(
            localize_video.os.environ,
            {
                "VOLCENGINE_TTS_API_KEY": "api-key-123",
            },
            clear=True,
        ):
            with self.assertRaises(SystemExit) as exc:
                localize_video.build_volc_tts_request(
                    "你好，世界",
                    speaker="zh_female_cancan_mars_bigtts",
                    response_format="wav",
                    sample_rate=24000,
                )

        self.assertIn("VOLCENGINE_TTS_RESOURCE_ID", str(exc.exception))
        self.assertIn("VOLCENGINE_TTS_URL", str(exc.exception))

    def test_build_volc_tts_request_supports_legacy_access_key_auth(self) -> None:
        with mock.patch.dict(
            localize_video.os.environ,
            {
                "VOLCENGINE_TTS_APP_ID": "app-id-123",
                "VOLCENGINE_TTS_ACCESS_KEY": "access-key-456",
                "VOLCENGINE_TTS_RESOURCE_ID": "custom.resource",
            },
            clear=True,
        ):
            request = localize_video.build_volc_tts_request(
                "你好，世界",
                speaker="zh_female_qingxin",
                response_format="wav",
                sample_rate=24000,
            )

        self.assertEqual(
            "app-id-123",
            request.headers["X-api-app-id"],
        )
        self.assertEqual(
            "access-key-456",
            request.headers["X-api-access-key"],
        )
        self.assertEqual(
            "custom.resource",
            request.headers["X-api-resource-id"],
        )
        self.assertNotIn("X-api-key", request.headers)

    def test_build_volc_tts_request_prefers_api_key_over_legacy_auth(self) -> None:
        with mock.patch.dict(
            localize_video.os.environ,
            {
                "VOLCENGINE_TTS_API_KEY": "api-key-123",
                "VOLCENGINE_TTS_RESOURCE_ID": "resource-123",
                "VOLCENGINE_TTS_URL": "https://ark.example.com/api/v1/tts",
                "VOLCENGINE_TTS_APP_ID": "app-id-123",
                "VOLCENGINE_TTS_ACCESS_KEY": "access-key-456",
            },
            clear=True,
        ):
            request = localize_video.build_volc_tts_request(
                "你好，世界",
                speaker="zh_female_cancan_mars_bigtts",
                response_format="wav",
                sample_rate=24000,
            )

        self.assertEqual("api-key-123", request.headers["X-api-key"])
        self.assertNotIn("X-api-app-id", request.headers)
        self.assertNotIn("X-api-access-key", request.headers)

    def test_parse_tts_response_returns_binary_audio_content(self) -> None:
        result = localize_video.parse_tts_response(
            b"binary-audio",
            content_type="audio/wav",
        )

        self.assertEqual(b"binary-audio", result)

    def test_parse_tts_response_supports_json_base64_audio(self) -> None:
        payload = json.dumps(
            {
                "audio": {
                    "data": "YXVkaW8tYnl0ZXM=",
                }
            }
        ).encode("utf-8")

        result = localize_video.parse_tts_response(
            payload,
            content_type="application/json",
        )

        self.assertEqual(b"audio-bytes", result)

    def test_load_segments_from_srt_parses_multiline_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            srt_path = Path(tmpdir) / "lesson_en.srt"
            srt_path.write_text(
                "\n".join(
                    [
                        "1",
                        "00:00:00,000 --> 00:00:02,500",
                        "Hello there.",
                        "",
                        "2",
                        "00:00:03,000 --> 00:00:05,000",
                        "This is line one.",
                        "This is line two.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            segments = localize_video.load_segments_from_srt(srt_path)

        self.assertEqual(2, len(segments))
        self.assertEqual(0.0, segments[0].start)
        self.assertEqual(2.5, segments[0].end)
        self.assertEqual("Hello there.", segments[0].text)
        self.assertEqual("This is line one. This is line two.", segments[1].text)

    def test_resolve_input_srt_prefers_sibling_en_subtitle_for_local_video(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "lesson.mp4"
            subtitle_path = Path(tmpdir) / "lesson_en.srt"
            video_path.write_bytes(b"video")
            subtitle_path.write_text("", encoding="utf-8")

            resolved = localize_video.resolve_input_srt(video_path)

        self.assertEqual(subtitle_path, resolved)

    def test_resolve_input_srt_errors_when_local_video_has_no_subtitle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "lesson.mp4"
            video_path.write_bytes(b"video")

            with self.assertRaises(SystemExit) as exc:
                localize_video.resolve_input_srt(video_path)

        self.assertIn("requires --input-srt", str(exc.exception))

    def test_finalize_audio_copies_dub_track_when_muting_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_audio = Path(tmpdir) / "audio.wav"
            dub_track = Path(tmpdir) / "dub.wav"
            output_path = Path(tmpdir) / "final.wav"
            original_audio.write_bytes(b"original")
            dub_track.write_bytes(b"dub")

            with mock.patch.object(localize_video, "mix_with_original_audio") as mix_audio:
                localize_video.finalize_audio(
                    original_audio,
                    dub_track,
                    output_path,
                    mute_original_audio=True,
                    background_volume=0.12,
                )

            copied_bytes = output_path.read_bytes()

        mix_audio.assert_not_called()
        self.assertEqual(b"dub", copied_bytes)


if __name__ == "__main__":
    unittest.main()
