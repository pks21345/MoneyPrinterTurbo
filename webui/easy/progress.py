"""Task progress projection for the Korean-first MPT Easy UI.

This module intentionally keeps Streamlit out of the task-state model so the
progress semantics can be unit-tested without a browser runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from app.models import const


class EasyTaskState(str, Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class EasyStepState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class _StageSpec:
    key: str
    label_ko: str
    start_progress: int
    complete_progress: int


@dataclass(frozen=True, slots=True)
class EasyProgressStep:
    key: str
    label_ko: str
    state: EasyStepState


@dataclass(frozen=True, slots=True)
class EasyTaskSnapshot:
    task_id: str
    state: EasyTaskState
    progress: int
    current_stage_ko: str
    steps: tuple[EasyProgressStep, ...]
    videos: tuple[str, ...] = ()
    warnings: tuple[Any, ...] = ()
    error: str = ""
    failed_stage: str = ""

    @property
    def terminal(self) -> bool:
        return self.state in {EasyTaskState.COMPLETE, EasyTaskState.FAILED}


_STAGE_SPECS = (
    _StageSpec("script", "문안 생성", 1, 10),
    _StageSpec("terms", "검색어 구성", 10, 20),
    _StageSpec("audio", "음성 생성", 20, 30),
    _StageSpec("subtitle", "자막 생성", 30, 40),
    _StageSpec("materials", "영상 소재 준비", 40, 50),
    _StageSpec("video", "영상 합성", 50, 100),
)

_FAILURE_STAGE_LABELS = {
    "preflight": "생성 전 최종 점검",
    "script": "문안 생성",
    "terms": "검색어 구성",
    "audio": "음성 생성",
    "subtitle": "자막 생성",
    "materials": "영상 소재 준비",
    "video": "영상 합성",
    "scheduling": "작업 접수",
    "webui_worker": "영상 생성 엔진",
}


def _clamp_progress(value: Any) -> int:
    try:
        progress = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, progress))


def _normalize_state(task: Mapping[str, Any] | None) -> EasyTaskState:
    if not task:
        return EasyTaskState.WAITING

    state = task.get("state")
    if state == const.TASK_STATE_COMPLETE:
        return EasyTaskState.COMPLETE
    if state == const.TASK_STATE_FAILED:
        return EasyTaskState.FAILED
    return EasyTaskState.PROCESSING


def _current_stage_label(
    state: EasyTaskState,
    progress: int,
    failed_stage: str,
) -> str:
    if state == EasyTaskState.WAITING:
        return "작업 접수 확인 중"
    if state == EasyTaskState.COMPLETE:
        return "영상 완성"
    if state == EasyTaskState.FAILED:
        return _FAILURE_STAGE_LABELS.get(failed_stage, "영상 생성")
    if progress <= 0:
        return "작업 대기"

    for stage in reversed(_STAGE_SPECS):
        if progress >= stage.start_progress:
            return stage.label_ko
    return "작업 대기"


def _build_steps(
    state: EasyTaskState,
    progress: int,
    failed_stage: str,
) -> tuple[EasyProgressStep, ...]:
    steps: list[EasyProgressStep] = []
    for stage in _STAGE_SPECS:
        if state == EasyTaskState.COMPLETE:
            step_state = EasyStepState.COMPLETE
        elif state == EasyTaskState.FAILED and failed_stage == stage.key:
            step_state = EasyStepState.FAILED
        elif progress >= stage.complete_progress:
            step_state = EasyStepState.COMPLETE
        elif (
            state == EasyTaskState.PROCESSING
            and progress >= stage.start_progress
            and progress > 0
        ):
            step_state = EasyStepState.ACTIVE
        else:
            step_state = EasyStepState.PENDING

        steps.append(
            EasyProgressStep(
                key=stage.key,
                label_ko=stage.label_ko,
                state=step_state,
            )
        )
    return tuple(steps)


def build_easy_task_snapshot(
    task_id: str,
    task: Mapping[str, Any] | None,
) -> EasyTaskSnapshot:
    """Project canonical MPT task state into a stable Easy-facing snapshot."""

    state = _normalize_state(task)
    progress = _clamp_progress((task or {}).get("progress", 0))
    failed_stage = str((task or {}).get("failed_stage") or "").strip()
    error = str((task or {}).get("error") or "").strip()

    raw_videos = (task or {}).get("videos") or []
    if isinstance(raw_videos, (str, Path)):
        raw_videos = [raw_videos]
    videos = tuple(str(path) for path in raw_videos if path)

    raw_warnings = (task or {}).get("warnings") or []
    if isinstance(raw_warnings, (str, Mapping)):
        raw_warnings = [raw_warnings]

    return EasyTaskSnapshot(
        task_id=task_id,
        state=state,
        progress=100 if state == EasyTaskState.COMPLETE else progress,
        current_stage_ko=_current_stage_label(state, progress, failed_stage),
        steps=_build_steps(state, progress, failed_stage),
        videos=videos,
        warnings=tuple(raw_warnings),
        error=error,
        failed_stage=failed_stage,
    )


def get_easy_task_snapshot(
    task_id: str,
    *,
    task_getter: Callable[[str], Mapping[str, Any] | None] | None = None,
) -> EasyTaskSnapshot:
    """Read one task from the existing MPT state service and project it for Easy."""

    if task_getter is None:
        from app.services import state as state_service

        effective_getter = state_service.state.get_task
    else:
        effective_getter = task_getter

    return build_easy_task_snapshot(task_id, effective_getter(task_id))


def safe_result_video_paths(
    task_id: str,
    video_paths: Sequence[str],
    *,
    task_root: str | Path | None = None,
) -> tuple[Path, ...]:
    """Return existing final videos constrained to the task's own storage folder."""

    if task_root is None:
        from app.utils import utils

        root = Path(utils.task_dir()).resolve()
    else:
        root = Path(task_root).resolve()

    task_dir = (root / task_id).resolve()
    try:
        task_dir.relative_to(root)
    except ValueError:
        return ()

    safe_paths: list[Path] = []
    for raw_path in video_paths:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        try:
            candidate.relative_to(task_dir)
        except ValueError:
            continue
        if candidate.is_file():
            safe_paths.append(candidate)

    return tuple(safe_paths)
