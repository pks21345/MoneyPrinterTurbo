"""UI-facing labels and adapters for the Korean-first MPT Easy screen.

This module contains no Streamlit dependency so its behavior can be unit tested
without starting a WebUI runtime. The canonical generation contract remains
``VideoParams`` built by :mod:`webui.easy.presets`.
"""

from dataclasses import dataclass
from typing import Mapping

from app.models.schema import VideoAspect, VideoParams
from webui.easy.presets import (
    CONTENT_PRESETS,
    DURATION_PROFILES,
    EasyContentPreset,
    EasyDuration,
    build_video_params,
)


@dataclass(frozen=True, slots=True)
class EasyVoiceOption:
    voice_id: str
    label_ko: str
    description_ko: str


@dataclass(frozen=True, slots=True)
class EasyAspectOption:
    aspect: VideoAspect
    label_ko: str
    description_ko: str


VOICE_OPTIONS: tuple[EasyVoiceOption, ...] = (
    EasyVoiceOption(
        voice_id="ko-KR-SunHiNeural-Female",
        label_ko="한국어 여성 · 선희",
        description_ko="자연스러운 기본 한국어 여성 음성",
    ),
    EasyVoiceOption(
        voice_id="ko-KR-InJoonNeural-Male",
        label_ko="한국어 남성 · 인준",
        description_ko="차분한 한국어 남성 음성",
    ),
    EasyVoiceOption(
        voice_id="ko-KR-HyunsuMultilingualNeural-Male",
        label_ko="한국어 남성 · 현수",
        description_ko="다국어 발음도 지원하는 한국어 남성 음성",
    ),
)

ASPECT_OPTIONS: tuple[EasyAspectOption, ...] = (
    EasyAspectOption(
        aspect=VideoAspect.portrait,
        label_ko="세로 9:16",
        description_ko="유튜브 쇼츠·릴스·틱톡용 기본 비율",
    ),
    EasyAspectOption(
        aspect=VideoAspect.landscape,
        label_ko="가로 16:9",
        description_ko="일반 유튜브 영상용 비율",
    ),
    EasyAspectOption(
        aspect=VideoAspect.square,
        label_ko="정사각형 1:1",
        description_ko="피드형 콘텐츠용 비율",
    ),
)

VOICE_BY_ID: Mapping[str, EasyVoiceOption] = {
    option.voice_id: option for option in VOICE_OPTIONS
}
ASPECT_BY_VALUE: Mapping[str, EasyAspectOption] = {
    option.aspect.value: option for option in ASPECT_OPTIONS
}


def content_label(value: str) -> str:
    return CONTENT_PRESETS[EasyContentPreset(value)].label_ko


def duration_label(value: str) -> str:
    return DURATION_PROFILES[EasyDuration(value)].label_ko


def voice_label(voice_id: str) -> str:
    return VOICE_BY_ID[voice_id].label_ko


def aspect_label(aspect_value: str) -> str:
    return ASPECT_BY_VALUE[aspect_value].label_ko


def build_params_from_ui(
    topic: str,
    *,
    content_preset: str,
    duration: str,
    aspect: str,
    voice_id: str,
) -> VideoParams:
    """Translate stable UI values into the tested Easy preset builder."""

    if voice_id not in VOICE_BY_ID:
        raise ValueError(f"지원하지 않는 음성입니다: {voice_id!r}")
    if aspect not in ASPECT_BY_VALUE:
        raise ValueError(f"지원하지 않는 화면 비율입니다: {aspect!r}")

    return build_video_params(
        topic,
        content_preset=content_preset,
        duration=duration,
        aspect=VideoAspect(aspect),
        voice_name=voice_id,
    )


def summarize_params(params: VideoParams) -> dict[str, str | int | bool]:
    """Return a small Korean-friendly summary without exposing internal noise."""

    voice_id = str(params.voice_name or "")
    return {
        "주제": params.video_subject,
        "화면": aspect_label(
            params.video_aspect.value
            if isinstance(params.video_aspect, VideoAspect)
            else str(params.video_aspect)
        ),
        "음성": voice_label(voice_id) if voice_id in VOICE_BY_ID else voice_id,
        "클립 길이 프로필": f"약 {params.video_clip_duration}초/장면",
        "스크립트 문단": params.paragraph_number,
        "자막": bool(params.subtitle_enabled),
        "생성 개수": params.video_count,
    }
