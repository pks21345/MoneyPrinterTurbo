"""Preflight checks for submitting an MPT Easy video generation task.

The checks mirror requirements already enforced by the upstream generation
pipeline, but translate them into small Korean-first status items before a task
is queued. No network calls are performed here.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from app.config import config
from app.models.llm_provider import DEFAULT_LLM_PROVIDER_ID, get_llm_provider
from app.models.schema import VideoParams


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    code: str
    label_ko: str
    ready: bool
    detail_ko: str
    action_ko: str = ""


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    checks: tuple[ReadinessCheck, ...]

    @property
    def ready(self) -> bool:
        return all(check.ready for check in self.checks)

    @property
    def blockers(self) -> tuple[ReadinessCheck, ...]:
        return tuple(check for check in self.checks if not check.ready)


def _effective_app_config(app_config: Mapping[str, Any] | None) -> dict[str, Any]:
    if app_config is not None:
        return dict(app_config)
    return config.snapshot_config_with_pending(config.app)


def _has_configured_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return any(str(item).strip() for item in value)
    return bool(value)


def _llm_readiness(app_config: Mapping[str, Any]) -> ReadinessCheck:
    provider_id = str(
        app_config.get("llm_provider", DEFAULT_LLM_PROVIDER_ID)
        or DEFAULT_LLM_PROVIDER_ID
    ).strip().lower()
    provider = get_llm_provider(provider_id)
    if provider is None:
        return ReadinessCheck(
            code="llm_provider",
            label_ko="AI 문안 생성",
            ready=False,
            detail_ko=f"지원하지 않는 LLM Provider가 선택되어 있습니다: {provider_id}",
            action_ko="기존 고급 WebUI에서 LLM Provider를 다시 선택해 주세요.",
        )

    missing: list[str] = []
    api_key = app_config.get(provider.config_key("api_key"), "")
    model_name = provider.resolve_model_name(
        app_config.get(provider.config_key("model_name"), "")
    )
    base_url = provider.resolve_base_url(
        app_config.get(provider.config_key("base_url"), "")
    )

    if provider.requires_api_key and not _has_configured_value(api_key):
        missing.append("API Key")
    if provider.requires_model_name and not str(model_name or "").strip():
        missing.append("모델 이름")
    # Ollama resolves its environment-specific base URL inside app.services.llm.
    if provider_id != "ollama" and provider.requires_base_url and not str(
        base_url or ""
    ).strip():
        missing.append("Base URL")

    for field in provider.extra_fields:
        configured = app_config.get(provider.config_key(field.config_suffix), "")
        effective = configured or field.default_value
        if field.required and not _has_configured_value(effective):
            missing.append(field.config_suffix)

    if missing:
        return ReadinessCheck(
            code="llm_provider",
            label_ko="AI 문안 생성",
            ready=False,
            detail_ko=f"{provider.default_label}: {', '.join(missing)} 설정이 필요합니다.",
            action_ko="위의 MPT Easy 시작 설정 또는 기존 고급 WebUI에서 AI Provider를 설정해 주세요.",
        )

    return ReadinessCheck(
        code="llm_provider",
        label_ko="AI 문안 생성",
        ready=True,
        detail_ko=f"{provider.default_label} 설정을 사용할 수 있습니다.",
    )


def _material_readiness(
    params: VideoParams, app_config: Mapping[str, Any]
) -> ReadinessCheck:
    source = str(params.video_source or "").strip().lower()
    key_config = {
        "pexels": ("pexels_api_keys", "Pexels"),
        "pixabay": ("pixabay_api_keys", "Pixabay"),
        "coverr": ("coverr_api_keys", "Coverr"),
    }

    if source in key_config:
        key_name, label = key_config[source]
        if not _has_configured_value(app_config.get(key_name, "")):
            return ReadinessCheck(
                code="video_material",
                label_ko="영상 소재",
                ready=False,
                detail_ko=f"기본 영상소스 {label}의 API Key가 필요합니다.",
                action_ko="Pexels는 위의 MPT Easy 시작 설정에서, 다른 영상소스는 기존 고급 WebUI에서 설정해 주세요.",
            )
        return ReadinessCheck(
            code="video_material",
            label_ko="영상 소재",
            ready=True,
            detail_ko=f"{label} 영상소스를 사용할 수 있습니다.",
        )

    if source == "local":
        has_materials = bool(params.video_materials)
        return ReadinessCheck(
            code="video_material",
            label_ko="영상 소재",
            ready=has_materials,
            detail_ko=(
                "로컬 영상 소재가 준비되어 있습니다."
                if has_materials
                else "로컬 영상소스를 선택했지만 업로드된 소재가 없습니다."
            ),
            action_ko=(
                "기존 고급 WebUI에서 로컬 영상을 먼저 업로드해 주세요."
                if not has_materials
                else ""
            ),
        )

    if source == "loomloom":
        return ReadinessCheck(
            code="video_material",
            label_ko="영상 소재",
            ready=False,
            detail_ko="LoomLoom은 생성 전 견적과 과금 확인이 필요합니다.",
            action_ko="v0.1 Easy 모드에서는 기존 고급 WebUI에서 사용해 주세요.",
        )

    return ReadinessCheck(
        code="video_material",
        label_ko="영상 소재",
        ready=False,
        detail_ko=f"지원하지 않는 영상소스입니다: {source or '(없음)'}",
        action_ko="기존 고급 WebUI에서 영상소스를 다시 선택해 주세요.",
    )


def check_generation_readiness(
    params: VideoParams,
    *,
    app_config: Mapping[str, Any] | None = None,
) -> ReadinessReport:
    """Return config-only preflight checks for an Easy video generation task."""

    effective_config = _effective_app_config(app_config)
    subject_ready = bool(
        str(params.video_subject or "").strip() or str(params.video_script or "").strip()
    )
    subject_check = ReadinessCheck(
        code="subject",
        label_ko="영상 주제",
        ready=subject_ready,
        detail_ko=(
            "영상 주제가 준비되어 있습니다."
            if subject_ready
            else "영상 주제 또는 스크립트가 필요합니다."
        ),
        action_ko="영상 주제를 한 글자 이상 입력해 주세요." if not subject_ready else "",
    )

    return ReadinessReport(
        checks=(
            subject_check,
            _llm_readiness(effective_config),
            _material_readiness(params, effective_config),
        )
    )
