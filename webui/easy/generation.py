"""Submission boundary from MPT Easy into the existing WebUI task engine."""

from dataclasses import dataclass
from typing import Any, Callable, Mapping
from uuid import uuid4

from app.config import config
from app.models.schema import VideoParams
from webui.easy.readiness import ReadinessReport, check_generation_readiness


class EasyGenerationNotReady(RuntimeError):
    """Raised when an Easy task is submitted before preflight requirements pass."""

    def __init__(self, report: ReadinessReport):
        self.report = report
        details = "; ".join(check.detail_ko for check in report.blockers)
        super().__init__(details or "영상 제작 준비가 완료되지 않았습니다.")


@dataclass(frozen=True, slots=True)
class EasyGenerationSubmission:
    task_id: str
    params: VideoParams
    readiness: ReadinessReport


def submit_easy_generation(
    params: VideoParams,
    *,
    app_config: Mapping[str, Any] | None = None,
    submitter: Callable[..., None] | None = None,
    task_id_factory: Callable[[], str] | None = None,
) -> EasyGenerationSubmission:
    """Validate readiness and enqueue a task in the canonical MPT WebUI engine."""

    readiness = check_generation_readiness(params, app_config=app_config)
    if not readiness.ready:
        raise EasyGenerationNotReady(readiness)

    task_id = (task_id_factory or (lambda: str(uuid4())))()
    if submitter is None:
        from app.services import webui_task

        effective_submitter = webui_task.submit_generation
    else:
        effective_submitter = submitter
    effective_submitter(
        task_id=task_id,
        params=params,
        capture_logs=not bool(config.ui.get("hide_log", False)),
    )
    return EasyGenerationSubmission(
        task_id=task_id,
        params=params.model_copy(deep=True),
        readiness=readiness,
    )
