import importlib.util
import http.client
import json
import sys
import tempfile
import unittest
import uuid
import urllib.error
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "localize_video.py"
SPEC = importlib.util.spec_from_file_location("localize_video", MODULE_PATH)
localize_video = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = localize_video
SPEC.loader.exec_module(localize_video)


class LocalizeVideoTests(unittest.TestCase):
    def test_parse_args_defaults_to_liufei_male_voice(self) -> None:
        args = localize_video.parse_args(
            ["--input", "lesson.mp4", "--workdir", "workdir"]
        )

        self.assertEqual("zh_male_liufei_uranus_bigtts", args.voice)

    def test_build_volc_tts_request_prefers_api_key_auth(self) -> None:
        with mock.patch.dict(
            localize_video.os.environ,
            {
                "VOLCENGINE_TTS_API_KEY": "api-key-123",
                "VOLCENGINE_TTS_RESOURCE_ID": "resource-123",
                "VOLCENGINE_TTS_URL": "https://openspeech.bytedance.com/api/v1/tts",
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
            "12345678-1234-5678-1234-567812345678",
            request.headers["X-api-request-id"],
        )
        self.assertEqual("https://openspeech.bytedance.com/api/v1/tts", request.full_url)
        self.assertNotIn("X-api-app-id", request.headers)
        self.assertNotIn("X-api-access-key", request.headers)
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual("resource-123", payload["app"]["appid"])
        self.assertEqual("volcano_tts", payload["app"]["cluster"])
        self.assertEqual("codex-localizer", payload["user"]["uid"])
        self.assertEqual("你好，世界", payload["request"]["text"])
        self.assertEqual("plain", payload["request"]["text_type"])
        self.assertEqual("query", payload["request"]["operation"])
        self.assertEqual("12345678-1234-5678-1234-567812345678", payload["request"]["reqid"])
        self.assertEqual("zh_female_cancan_mars_bigtts", payload["audio"]["voice_type"])
        self.assertEqual(1.0, payload["audio"]["speed_ratio"])
        self.assertEqual(1.0, payload["audio"]["volume_ratio"])
        self.assertEqual("wav", payload["audio"]["encoding"])

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
                "VOLCENGINE_TTS_URL": "https://openspeech.bytedance.com/api/v1/tts",
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
        self.assertNotIn("X-api-resource-id", request.headers)
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

    def test_read_tts_response_bytes_uses_partial_content_on_incomplete_read(self) -> None:
        response = mock.Mock()
        response.read.side_effect = http.client.IncompleteRead(b"partial-audio", 42)

        result = localize_video.read_tts_response_bytes(response)

        self.assertEqual(b"partial-audio", result)

    def test_open_tts_request_retries_transient_url_errors(self) -> None:
        first_error = urllib.error.URLError("temporary ssl eof")
        second_response = mock.Mock()
        second_response.__enter__ = mock.Mock(return_value=second_response)
        second_response.__exit__ = mock.Mock(return_value=False)
        second_response.read.return_value = b"ok"
        second_response.headers.get.return_value = "audio/wav"

        with mock.patch.object(
            localize_video.urllib.request,
            "urlopen",
            side_effect=[first_error, second_response],
        ) as urlopen_mock, mock.patch.object(localize_video.time, "sleep") as sleep_mock:
            with localize_video.open_tts_request(mock.Mock()) as response:
                payload = localize_video.read_tts_response_bytes(response)

        self.assertEqual(b"ok", payload)
        self.assertEqual(2, urlopen_mock.call_count)
        sleep_mock.assert_called_once()

    def test_synthesize_volc_tts_retries_truncated_json_response(self) -> None:
        truncated_response = mock.Mock()
        truncated_response.__enter__ = mock.Mock(return_value=truncated_response)
        truncated_response.__exit__ = mock.Mock(return_value=False)
        truncated_response.read.return_value = b'{"data":"YXVkaW8='
        truncated_response.headers.get.return_value = "application/json"

        valid_response = mock.Mock()
        valid_response.__enter__ = mock.Mock(return_value=valid_response)
        valid_response.__exit__ = mock.Mock(return_value=False)
        valid_response.read.return_value = b'{"data":"YXVkaW8tYnl0ZXM="}'
        valid_response.headers.get.return_value = "application/json"

        with mock.patch.object(
            localize_video,
            "build_volc_tts_request",
            return_value=mock.Mock(),
        ), mock.patch.object(
            localize_video,
            "open_tts_request",
            side_effect=[truncated_response, valid_response],
        ) as open_mock:
            result = localize_video.synthesize_volc_tts(
                "你好，世界",
                speaker="zh_male_liufei_uranus_bigtts",
                response_format="wav",
                sample_rate=24000,
            )

        self.assertEqual(b"audio-bytes", result)
        self.assertEqual(2, open_mock.call_count)

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
