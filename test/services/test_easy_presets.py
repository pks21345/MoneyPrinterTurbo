import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.schema import VideoAspect, VideoParams
from webui.easy.presets import (
    CONTENT_PRESETS,
    DURATION_PROFILES,
    EasyContentPreset,
    EasyDuration,
    EasyPresetError,
    build_video_params,
)


class TestEasyPresets(unittest.TestCase):
    def test_every_content_preset_builds_valid_video_params(self):
        for preset in EasyContentPreset:
            with self.subTest(preset=preset):
                params = build_video_params("여름철 전기요금 줄이는 방법", content_preset=preset)

                self.assertIsInstance(params, VideoParams)
                self.assertEqual(params.video_aspect, VideoAspect.portrait)
                self.assertEqual(params.video_count, 1)
                self.assertTrue(params.subtitle_enabled)

    def test_korean_labels_are_accepted(self):
        for preset in CONTENT_PRESETS.values():
            with self.subTest(preset=preset.label_ko):
                params = build_video_params("커피 상식", content_preset=preset.label_ko)
                self.assertEqual(params.video_subject, "커피 상식")

        for profile in DURATION_PROFILES.values():
            with self.subTest(duration=profile.label_ko):
                params = build_video_params("커피 상식", duration=profile.label_ko)
                self.assertGreaterEqual(params.video_clip_duration, 1)

    def test_duration_profiles_are_deterministic(self):
        expected = {
            EasyDuration.SHORT: (3, 1),
            EasyDuration.NORMAL: (5, 1),
            EasyDuration.LONG: (7, 2),
        }

        for duration, (clip_duration, paragraph_number) in expected.items():
            with self.subTest(duration=duration):
                params = build_video_params("서울 여행", duration=duration)
                self.assertEqual(params.video_clip_duration, clip_duration)
                self.assertEqual(params.paragraph_number, paragraph_number)

    def test_tips_list_uses_shorter_clips_than_information(self):
        information = build_video_params(
            "정리 팁", content_preset=EasyContentPreset.INFORMATION
        )
        tips = build_video_params(
            "정리 팁", content_preset=EasyContentPreset.TIPS_LIST
        )

        self.assertEqual(
            tips.video_clip_duration,
            information.video_clip_duration - 1,
        )

    def test_free_preset_preserves_upstream_defaults_where_not_overridden(self):
        params = build_video_params(
            "자유 주제",
            content_preset=EasyContentPreset.FREE,
        )
        upstream_defaults = VideoParams(video_subject="baseline")

        self.assertEqual(params.video_concat_mode, upstream_defaults.video_concat_mode)
        self.assertEqual(params.bgm_type, upstream_defaults.bgm_type)
        self.assertEqual(params.bgm_volume, upstream_defaults.bgm_volume)
        self.assertEqual(params.voice_name, upstream_defaults.voice_name)

    def test_voice_name_is_optional_and_trimmed_when_supplied(self):
        default_params = build_video_params("기본 음성")
        selected_params = build_video_params(
            "선택 음성", voice_name="  ko-KR-SunHiNeural-Female  "
        )

        self.assertEqual(default_params.voice_name, "")
        self.assertEqual(selected_params.voice_name, "ko-KR-SunHiNeural-Female")

    def test_empty_topic_fails_with_clear_error(self):
        for topic in ("", "   "):
            with self.subTest(topic=topic):
                with self.assertRaisesRegex(EasyPresetError, "영상 주제"):
                    build_video_params(topic)

    def test_unknown_content_preset_fails_with_clear_error(self):
        with self.assertRaisesRegex(EasyPresetError, "콘텐츠 프리셋"):
            build_video_params("테스트", content_preset="unknown")

    def test_unknown_duration_fails_with_clear_error(self):
        with self.assertRaisesRegex(EasyPresetError, "길이 프리셋"):
            build_video_params("테스트", duration="unknown")

    def test_preset_data_contains_no_secret_fields(self):
        serialized = repr((CONTENT_PRESETS, DURATION_PROFILES)).lower()
        for secret_name in ("api_key", "token", "secret", "password"):
            self.assertNotIn(secret_name, serialized)


if __name__ == "__main__":
    unittest.main()
