"""First-run configuration helpers for MPT Easy.

The Easy setup layer intentionally reuses MoneyPrinterTurbo's existing
``config.toml`` runtime configuration instead of introducing a second secret
store. Secrets are write-only from the Easy UI: existing values are never
returned to the browser for prefilling.
"""

from contextlib import nullcontext
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, ContextManager, Mapping, MutableMapping

import requests

from app.config import config
from app.models.llm_provider import get_llm_provider
from app.models.schema import VideoParams
from webui.easy.readiness import check_generation_readiness
from webui.easy.safety import redact_sensitive_text


@dataclass(frozen=True, slots=True)
class EasyProviderChoice:
    provider_id: str
    label_ko: str
    description_ko: str


PROVIDER_CHOICES = (
    EasyProviderChoice(
        provider_id="moonshot",
        label_ko="Kimi / Moonshot AI",
        description_ko="MoneyPrinterTurbo 기본 Provider입니다. 기존 Kimi 설정을 그대로 사용합니다.",
    ),
    EasyProviderChoice(
        provider_id="openai",
        label_ko="OpenAI",
        description_ko="OpenAI API Key를 사용합니다. 모델과 Base URL은 MPT 기본값을 따릅니다.",
    ),
    EasyProviderChoice(
        provider_id="gemini",
        label_ko="Google Gemini",
        description_ko="Google AI Studio API Key를 사용합니다. Base URL 입력은 필요하지 않습니다.",
    ),
    EasyProviderChoice(
        provider_id="ollama",
        label_ko="Ollama · 로컬",
        description_ko="API Key 없이 로컬 Ollama를 사용합니다. 설치된 모델 이름은 직접 입력해야 합니다.",
    ),
)
_PROVIDER_CHOICE_MAP = {choice.provider_id: choice for choice in PROVIDER_CHOICES}


@dataclass(frozen=True, slots=True)
class EasySetupSnapshot:
    provider_id: str
    provider_label: str
    llm_configured: bool
    pexels_configured: bool
    ready: bool
    model_name: str = ""


@dataclass(frozen=True, slots=True)
class EasySetupSaveResult:
    saved_immediately: bool
    provider_id: str
    llm_secret_changed: bool
    pexels_secret_changed: bool


@dataclass(frozen=True, slots=True)
class EasyConnectionResult:
    code: str
    label_ko: str
    success: bool | None
    detail_ko: str
    elapsed_seconds: float | None = None


class EasySetupError(ValueError):
    """Raised when first-run setup input is invalid."""


def _effective_config(app_config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if app_config is not None:
        return dict(app_config)
    return config.snapshot_config_with_pending(config.app)


def _configured(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return any(str(item).strip() for item in value)
    return bool(value)


def _first_api_key(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        for item in value:
            normalized = str(item).strip()
            if normalized:
                return normalized
    return ""


def provider_label(provider_id: str) -> str:
    choice = _PROVIDER_CHOICE_MAP.get((provider_id or "").strip().lower())
    return choice.label_ko if choice else provider_id


def provider_api_key_url(provider_id: str) -> str:
    provider = _normalize_provider(provider_id)
    return provider.effective_api_key_url(prefer_international=True)


def get_easy_setup_snapshot(
    app_config: Mapping[str, Any] | None = None,
) -> EasySetupSnapshot:
    effective = _effective_config(app_config)
    provider_id = str(effective.get("llm_provider", "moonshot") or "moonshot").lower()
    provider = get_llm_provider(provider_id)

    dummy_params = VideoParams(video_subject="MPT Easy setup check")
    report = check_generation_readiness(dummy_params, app_config=effective)
    checks = {check.code: check for check in report.checks}

    model_name = ""
    if provider is not None:
        model_name = provider.resolve_model_name(
            effective.get(provider.config_key("model_name"), "")
        )

    return EasySetupSnapshot(
        provider_id=provider_id,
        provider_label=(provider.default_label if provider else provider_id),
        llm_configured=bool(checks["llm_provider"].ready),
        pexels_configured=_configured(effective.get("pexels_api_keys", [])),
        ready=report.ready,
        model_name=model_name,
    )


def _normalize_provider(provider_id: str):
    normalized = (provider_id or "").strip().lower()
    if normalized not in _PROVIDER_CHOICE_MAP:
        raise EasySetupError(f"Easy 설정에서 지원하지 않는 AI Provider입니다: {provider_id}")
    provider = get_llm_provider(normalized)
    if provider is None:
        raise EasySetupError(f"MoneyPrinterTurbo가 지원하지 않는 AI Provider입니다: {provider_id}")
    return provider


def build_easy_setup_updates(
    *,
    provider_id: str,
    llm_api_key: str = "",
    pexels_api_key: str = "",
    ollama_model_name: str = "",
    current_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the minimal config patch without returning or copying old secrets."""

    provider = _normalize_provider(provider_id)
    current = dict(current_config or {})
    updates: dict[str, Any] = {"llm_provider": provider.provider_id}

    entered_llm_key = (llm_api_key or "").strip()
    if provider.requires_api_key:
        existing_key = current.get(provider.config_key("api_key"), "")
        if entered_llm_key:
            updates[provider.config_key("api_key")] = entered_llm_key
        elif not _configured(existing_key):
            # Keep the field explicitly empty only when there is no prior secret.
            # This makes readiness deterministic while never copying another
            # provider's key into the selected provider.
            updates[provider.config_key("api_key")] = ""

    if provider.provider_id == "ollama":
        entered_model = (ollama_model_name or "").strip()
        existing_model = str(current.get(provider.config_key("model_name"), "") or "").strip()
        if entered_model:
            updates[provider.config_key("model_name")] = entered_model
        elif not existing_model:
            updates[provider.config_key("model_name")] = ""

    entered_pexels_key = (pexels_api_key or "").strip()
    if entered_pexels_key:
        updates["pexels_api_keys"] = [entered_pexels_key]
    elif not _configured(current.get("pexels_api_keys", [])):
        updates["pexels_api_keys"] = []

    return updates


def save_easy_setup(
    *,
    provider_id: str,
    llm_api_key: str = "",
    pexels_api_key: str = "",
    ollama_model_name: str = "",
    config_section: MutableMapping[str, Any] | None = None,
    update_func: Callable[[MutableMapping[str, Any], str, Any], bool] | None = None,
    save_func: Callable[[], bool] | None = None,
) -> EasySetupSaveResult:
    """Persist Easy setup into the canonical MPT ``[app]`` config section."""

    section = config_section if config_section is not None else config.app
    current = (
        dict(section)
        if config_section is not None
        else config.snapshot_config_with_pending(config.app)
    )
    updates = build_easy_setup_updates(
        provider_id=provider_id,
        llm_api_key=llm_api_key,
        pexels_api_key=pexels_api_key,
        ollama_model_name=ollama_model_name,
        current_config=current,
    )
    updater = update_func or config.update_config_nonblocking
    saver = save_func or config.try_save_config

    all_immediate = True
    for key, value in updates.items():
        all_immediate = bool(updater(section, key, value)) and all_immediate
    saved_immediately = bool(saver()) and all_immediate

    provider = _normalize_provider(provider_id)
    return EasySetupSaveResult(
        saved_immediately=saved_immediately,
        provider_id=provider.provider_id,
        llm_secret_changed=(
            provider.requires_api_key and bool((llm_api_key or "").strip())
        ),
        pexels_secret_changed=bool((pexels_api_key or "").strip()),
    )


def check_pexels_connection(
    api_key: str,
    *,
    request_get: Callable[..., Any] = requests.get,
    timeout_seconds: float = 10.0,
    tls_verify: bool = True,
) -> tuple[bool, str, float]:
    """Send one minimal Pexels video-search request without logging the secret."""

    normalized_key = (api_key or "").strip()
    if not normalized_key:
        return False, "Pexels API Key가 없습니다.", 0.0

    started_at = perf_counter()
    try:
        response = request_get(
            "https://api.pexels.com/v1/videos/search",
            headers={"Authorization": normalized_key},
            params={"query": "nature", "per_page": 1},
            timeout=timeout_seconds,
            verify=tls_verify,
        )
        elapsed = perf_counter() - started_at
    except requests.RequestException as exc:
        return False, f"Pexels 연결 실패: {type(exc).__name__}", perf_counter() - started_at
    except Exception as exc:
        return False, f"Pexels 연결 실패: {type(exc).__name__}", perf_counter() - started_at

    status_code = int(getattr(response, "status_code", 0) or 0)
    if status_code == 200:
        return True, "Pexels API 연결에 성공했습니다.", elapsed
    if status_code in {401, 403}:
        return False, "Pexels API Key가 올바르지 않거나 권한이 없습니다.", elapsed
    if status_code == 429:
        return False, "Pexels 요청 한도에 도달했습니다. 잠시 후 다시 확인해 주세요.", elapsed
    return False, f"Pexels가 HTTP {status_code or '오류'}로 응답했습니다.", elapsed


def check_easy_connections(
    *,
    app_config: Mapping[str, Any] | None = None,
    llm_tester: Callable[[], tuple[bool, str, float]] | None = None,
    pexels_tester: Callable[[str], tuple[bool, str, float]] | None = None,
    lock_factory: Callable[[], ContextManager[bool]] | None = None,
) -> tuple[EasyConnectionResult, EasyConnectionResult]:
    """Test saved LLM and Pexels settings without exposing credential values."""

    effective = _effective_config(app_config)
    snapshot = get_easy_setup_snapshot(effective)
    provider = get_llm_provider(snapshot.provider_id)

    if provider is None:
        llm_result = EasyConnectionResult(
            code="llm",
            label_ko="AI 모델",
            success=False,
            detail_ko="선택된 AI Provider를 확인할 수 없습니다.",
        )
    elif not snapshot.llm_configured:
        llm_result = EasyConnectionResult(
            code="llm",
            label_ko="AI 모델",
            success=False,
            detail_ko="먼저 AI Provider의 필수 설정을 저장해 주세요.",
        )
    else:
        llm_result = None

    pexels_key = _first_api_key(effective.get("pexels_api_keys", []))
    if not pexels_key:
        pexels_result = EasyConnectionResult(
            code="pexels",
            label_ko="영상 소재 · Pexels",
            success=False,
            detail_ko="먼저 Pexels API Key를 저장해 주세요.",
        )
    else:
        pexels_result = None

    if llm_result is not None and pexels_result is not None:
        return llm_result, pexels_result

    if llm_result is None and llm_tester is None:
        from app.services import llm as llm_service

        llm_tester = llm_service.test_connection
    if pexels_result is None and pexels_tester is None:
        tls_verify = bool(effective.get("tls_verify", True))

        def pexels_tester(key: str) -> tuple[bool, str, float]:
            return check_pexels_connection(key, tls_verify=tls_verify)

    locker = lock_factory or config.try_runtime_config_lock
    with locker() as lock_acquired:
        if not lock_acquired:
            busy_llm = llm_result or EasyConnectionResult(
                code="llm",
                label_ko="AI 모델",
                success=None,
                detail_ko="영상 생성 작업이 설정을 사용 중입니다. 완료 후 다시 확인해 주세요.",
            )
            busy_pexels = pexels_result or EasyConnectionResult(
                code="pexels",
                label_ko="영상 소재 · Pexels",
                success=None,
                detail_ko="영상 생성 작업이 설정을 사용 중입니다. 완료 후 다시 확인해 주세요.",
            )
            return busy_llm, busy_pexels

        if llm_result is None:
            try:
                ok, error, elapsed = llm_tester()
            except Exception as exc:
                ok, error, elapsed = False, type(exc).__name__, None
            llm_result = EasyConnectionResult(
                code="llm",
                label_ko=f"AI 모델 · {snapshot.provider_label}",
                success=ok,
                detail_ko=(
                    "AI 모델 연결에 성공했습니다."
                    if ok
                    else f"AI 모델 연결 실패: {redact_sensitive_text(error or '응답을 확인하지 못했습니다.')}"
                ),
                elapsed_seconds=elapsed,
            )

        if pexels_result is None:
            try:
                ok, detail, elapsed = pexels_tester(pexels_key)
            except Exception as exc:
                ok, detail, elapsed = False, f"Pexels 연결 실패: {type(exc).__name__}", None
            pexels_result = EasyConnectionResult(
                code="pexels",
                label_ko="영상 소재 · Pexels",
                success=ok,
                detail_ko=redact_sensitive_text(detail),
                elapsed_seconds=elapsed,
            )

    return llm_result, pexels_result


# Tests that inject fake testers do not need to acquire the global runtime lock.
def NOOP_CONNECTION_LOCK() -> ContextManager[bool]:
    return nullcontext(True)
