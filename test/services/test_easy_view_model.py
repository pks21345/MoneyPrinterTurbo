import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.schema import VideoAspect, VideoParams
from webui.easy.view_model import (
    ASPECT_OPTIONS,
    VOICE_OPTIONS,
    aspect_label,
    build_params_from_ui,
    content_label,
    duration_label,
    summarize_params,
    voice_label,
)


class TestEasyViewModel(unittest.TestCase):
    def test_default_ui_shape_builds_video_params(self):
        params = build_params_from_ui(
            "여름철 전기요금 줄이기",
            content_preset="information",
            duration="normal",
            aspect="9:16",
            voice_id="ko-KR-SunHiNeural-Female",
        )

        self.assertIsInstance(params, VideoParams)
        self.assertEqual(params.video_aspect, VideoAspect.portrait)
        self.assertEqual(params.voice_name, "ko-KR-SunHiNeural-Female")
        self.assertEqual(params.video_count, 1)

    def test_all_declared_voice_options_map_cleanly(self):
        for option in VOICE_OPTIONS:
            with self.subTest(voice=option.voice_id):
                params = build_params_from_ui(
                    "음성 테스트",
                    content_preset="information",
                    duration="normal",
                    aspect="9:16",
                    voice_id=option.voice_id,
                )
                self.assertEqual(params.voice_name, option.voice_id)
                self.assertEqual(voice_label(option.voice_id), option.label_ko)

    def test_all_aspect_options_map_cleanly(self):
        for option in ASPECT_OPTIONS:
            with self.subTest(aspect=option.aspect.value):
                params = build_params_from_ui(
                    "화면 테스트",
                    content_preset="free",
                    duration="short",
                    aspect=option.aspect.value,
                    voice_id=VOICE_OPTIONS[0].voice_id,
                )
                self.assertEqual(params.video_aspect, option.aspect)
                self.assertEqual(aspect_label(option.aspect.value), option.label_ko)

    def test_labels_are_korean_facing(self):
        self.assertEqual(content_label("information"), "정보형 쇼츠")
        self.assertEqual(duration_label("normal"), "보통")
        self.assertIn("한국어", voice_label(VOICE_OPTIONS[0].voice_id))
        self.assertEqual(aspect_label("9:16"), "세로 9:16")

    def test_unknown_voice_is_rejected_before_preset_builder(self):
        with self.assertRaisesRegex(ValueError, "음성"):
            build_params_from_ui(
                "테스트",
                content_preset="information",
                duration="normal",
                aspect="9:16",
                voice_id="unknown-voice",
            )

    def test_unknown_aspect_is_rejected_before_preset_builder(self):
        with self.assertRaisesRegex(ValueError, "화면 비율"):
            build_params_from_ui(
                "테스트",
                content_preset="information",
                duration="normal",
                aspect="4:3",
                voice_id=VOICE_OPTIONS[0].voice_id,
            )

    def test_summary_hides_internal_only_fields(self):
        params = build_params_from_ui(
            "요약 테스트",
            content_preset="tips_list",
            duration="long",
            aspect="9:16",
            voice_id=VOICE_OPTIONS[0].voice_id,
        )
        summary = summarize_params(params)

        self.assertEqual(summary["주제"], "요약 테스트")
        self.assertEqual(summary["화면"], "세로 9:16")
        self.assertTrue(summary["자막"])
        self.assertNotIn("video_script_prompt", summary)
        self.assertNotIn("custom_system_prompt", summary)


if __name__ == "__main__":
    unittest.main()
