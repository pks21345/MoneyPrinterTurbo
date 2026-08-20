"""Deterministic Easy-mode presets mapped to the canonical ``VideoParams`` model.

The Easy UI intentionally exposes only a few choices. All hidden values live in
this module so a Streamlit screen cannot silently drift from the tested defaults.
Duration profiles are approximate generation profiles, not exact output seconds.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from app.models.schema import VideoAspect, VideoConcatMode, VideoParams


class EasyPresetError(ValueError):
    """Raised when an Easy-mode request cannot be mapped deterministically."""


class EasyContentPreset(str, Enum):
    INFORMATION = "information"
    TIPS_LIST = "tips_list"
    FREE = "free"


class EasyDuration(str, Enum):
    SHORT = "short"
    NORMAL = "normal"
    LONG = "long"


@dataclass(frozen=True, slots=True)
class ContentPresetDefinition:
    key: EasyContentPreset
    label_ko: str
    description_ko: str
    clip_duration_offset: int = 0
    overrides: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DurationProfileDefinition:
    key: EasyDuration
    label_ko: str
    description_ko: str
    video_clip_duration: int
    paragraph_number: int


# These values deliberately stay close to the upstream VideoParams defaults.
# Easy mode is a UX layer, not a second generation engine.
CONTENT_PRESETS: Mapping[EasyContentPreset, ContentPresetDefinition] = {
    EasyContentPreset.INFORMATION: ContentPresetDefinition(
        key=EasyContentPreset.INFORMATION,
        label_ko="정보형 쇼츠",
        description_ko="설명과 핵심 정보를 빠르게 전달하는 기본 쇼츠",
        overrides={
            "video_concat_mode": VideoConcatMode.random.value,
            "subtitle_enabled": True,
            "video_count": 1,
        },
    ),
    EasyContentPreset.TIPS_LIST: ContentPresetDefinition(
        key=EasyContentPreset.TIPS_LIST,
        label_ko="꿀팁/리스트",
        description_ko="짧은 장면 전환으로 팁이나 목록을 빠르게 보여주는 쇼츠",
        clip_duration_offset=-1,
        overrides={
            "video_concat_mode": VideoConcatMode.random.value,
            "subtitle_enabled": True,
            "video_count": 1,
        },
    ),
    EasyContentPreset.FREE: ContentPresetDefinition(
        key=EasyContentPreset.FREE,
        label_ko="자유 제작",
        description_ko="원본 MoneyPrinterTurbo 기본값을 최대한 유지하는 자유형",
        overrides={
            "subtitle_enabled": True,
            "video_count": 1,
        },
    ),
}


DURATION_PROFILES: Mapping[EasyDuration, DurationProfileDefinition] = {
    EasyDuration.SHORT: DurationProfileDefinition(
        key=EasyDuration.SHORT,
        label_ko="짧게",
        description_ko="짧은 장면 중심의 간결한 프로필",
        video_clip_duration=3,
        paragraph_number=1,
    ),
    EasyDuration.NORMAL: DurationProfileDefinition(
        key=EasyDuration.NORMAL,
        label_ko="보통",
        description_ko="MoneyPrinterTurbo 기본 장면 길이에 가까운 표준 프로필",
        video_clip_duration=5,
        paragraph_number=1,
    ),
    EasyDuration.LONG: DurationProfileDefinition(
        key=EasyDuration.LONG,
        label_ko="길게",
        description_ko="조금 더 긴 장면과 스크립트 구성을 허용하는 프로필",
        video_clip_duration=7,
        paragraph_number=2,
    ),
}


def _resolve_content_preset(value: EasyContentPreset | str) -> ContentPresetDefinition:
    if isinstance(value, EasyContentPreset):
        return CONTENT_PRESETS[value]

    normalized = str(value).strip()
    for preset in CONTENT_PRESETS.values():
        if normalized in {preset.key.value, preset.label_ko}:
            return preset

    supported = ", ".join(preset.label_ko for preset in CONTENT_PRESETS.values())
    raise EasyPresetError(
        f"지원하지 않는 콘텐츠 프리셋입니다: {value!r}. 지원값: {supported}"
    )


def _resolve_duration(value: EasyDuration | str) -> DurationProfileDefinition:
    if isinstance(value, EasyDuration):
        return DURATION_PROFILES[value]

    normalized = str(value).strip()
    for profile in DURATION_PROFILES.values():
        if normalized in {profile.key.value, profile.label_ko}:
            return profile

    supported = ", ".join(profile.label_ko for profile in DURATION_PROFILES.values())
    raise EasyPresetError(
        f"지원하지 않는 길이 프리셋입니다: {value!r}. 지원값: {supported}"
    )


def build_video_params(
    topic: str,
    *,
    content_preset: EasyContentPreset | str = EasyContentPreset.INFORMATION,
    duration: EasyDuration | str = EasyDuration.NORMAL,
    aspect: VideoAspect | str = VideoAspect.portrait,
    voice_name: str | None = None,
) -> VideoParams:
    """Build a validated ``VideoParams`` instance for the Easy workflow.

    ``duration`` controls an approximate generation profile only. The final video
    length still depends on generated script, TTS, source materials, and the
    existing MoneyPrinterTurbo rendering pipeline.
    """

    normalized_topic = topic.strip() if isinstance(topic, str) else ""
    if not normalized_topic:
        raise EasyPresetError("영상 주제를 한 글자 이상 입력해 주세요.")

    preset = _resolve_content_preset(content_preset)
    duration_profile = _resolve_duration(duration)

    clip_duration = max(
        1,
        duration_profile.video_clip_duration + preset.clip_duration_offset,
    )

    params: dict[str, Any] = {
        "video_subject": normalized_topic,
        "video_aspect": aspect,
        "video_clip_duration": clip_duration,
        "paragraph_number": duration_profile.paragraph_number,
        **preset.overrides,
    }

    if voice_name is not None:
        params["voice_name"] = voice_name.strip()

    return VideoParams(**params)
