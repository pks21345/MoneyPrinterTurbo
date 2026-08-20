"""Korean-first Streamlit entry point for MPT Easy v0.1."""

import mimetypes
from pathlib import Path
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.models.schema import VideoParams  # noqa: E402
from webui.easy.generation import (  # noqa: E402
    EasyGenerationNotReady,
    submit_easy_generation,
)
from webui.easy.presets import (  # noqa: E402
    CONTENT_PRESETS,
    DURATION_PROFILES,
    EasyContentPreset,
    EasyDuration,
    EasyPresetError,
)
from webui.easy.readiness import (  # noqa: E402
    ReadinessReport,
    check_generation_readiness,
)
from webui.easy.safety import redact_sensitive_text, safe_exception_label  # noqa: E402
from webui.easy.setup import (  # noqa: E402
    PROVIDER_CHOICES,
    EasyConnectionResult,
    EasySetupError,
    get_easy_setup_snapshot,
    provider_api_key_url,
    provider_label,
    save_easy_setup,
    check_easy_connections,
)
from webui.easy.progress import (  # noqa: E402
    EasyStepState,
    EasyTaskSnapshot,
    EasyTaskState,
    get_easy_task_snapshot,
    safe_result_video_paths,
)
from webui.easy.view_model import (  # noqa: E402
    ASPECT_OPTIONS,
    VOICE_OPTIONS,
    aspect_label,
    build_params_from_ui,
    content_label,
    duration_label,
    summarize_params,
    voice_label,
)

st.set_page_config(
    page_title="MPT Easy",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container { max-width: 760px; padding-top: 2.5rem; padding-bottom: 4rem; }
    .mpt-hero { margin-bottom: 1.5rem; }
    .mpt-hero h1 { margin-bottom: .25rem; }
    .mpt-muted { color: #6b7280; font-size: .95rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _render_readiness(report: ReadinessReport) -> None:
    st.subheader("제작 준비 상태", divider="gray")
    for check in report.checks:
        if check.ready:
            st.success(f"✅ {check.label_ko} · {check.detail_ko}")
        else:
            st.warning(f"⚠️ {check.label_ko} · {check.detail_ko}")
            if check.action_ko:
                st.caption(check.action_ko)

    if report.ready:
        st.caption("필수 설정 검사를 통과했습니다. 실제 외부 서비스 연결은 생성 작업에서 확인됩니다.")
    else:
        st.info("위 항목을 준비한 뒤 다시 '영상 만들기'를 눌러 주세요.")



def _render_connection_result(result: EasyConnectionResult) -> None:
    elapsed = (
        f" · {result.elapsed_seconds:.2f}초"
        if result.elapsed_seconds is not None
        else ""
    )
    message = f"{result.label_ko} · {result.detail_ko}{elapsed}"
    if result.success is True:
        st.success(f"✅ {message}")
    elif result.success is False:
        st.error(f"❌ {message}")
    else:
        st.info(f"⏳ {message}")


def _render_easy_setup() -> None:
    snapshot = get_easy_setup_snapshot()
    if snapshot.ready:
        st.success(
            f"✅ 시작 준비 완료 · {snapshot.provider_label} + Pexels 설정이 준비되어 있습니다."
        )
    else:
        missing = []
        if not snapshot.llm_configured:
            missing.append("AI 모델")
        if not snapshot.pexels_configured:
            missing.append("Pexels")
        st.warning(
            "처음 한 번만 시작 설정이 필요합니다. "
            f"현재 필요한 항목: {', '.join(missing) or '설정 확인'}"
        )

    with st.expander("🔧 처음 설정 / API 연결", expanded=not snapshot.ready):
        provider_ids = [choice.provider_id for choice in PROVIDER_CHOICES]
        current_index = (
            provider_ids.index(snapshot.provider_id)
            if snapshot.provider_id in provider_ids
            else 0
        )
        selected_provider = st.selectbox(
            "AI 모델",
            options=provider_ids,
            index=current_index,
            format_func=provider_label,
            help="v0.1 Easy 설정에서는 자주 쓰는 Provider만 간단히 노출합니다.",
            key="mpt_easy_setup_provider",
        )
        provider_choice = next(
            choice for choice in PROVIDER_CHOICES if choice.provider_id == selected_provider
        )
        st.caption(provider_choice.description_ko)
        api_key_url = provider_api_key_url(selected_provider)
        if api_key_url:
            st.markdown(f"[AI API Key 발급 페이지 열기]({api_key_url})")
        st.markdown("[Pexels API Key 발급 페이지 열기](https://www.pexels.com/api/)")

        llm_api_key = ""
        ollama_model_name = ""
        if selected_provider == "ollama":
            ollama_model_name = st.text_input(
                "Ollama 모델 이름",
                value="",
                placeholder=snapshot.model_name or "예: qwen3:8b",
                help="이미 저장된 모델이 있으면 빈 칸으로 두어도 기존 값을 유지합니다.",
                key="mpt_easy_setup_ollama_model",
            )
        else:
            llm_api_key = st.text_input(
                "AI API Key",
                value="",
                type="password",
                placeholder=(
                    "저장된 Key가 있습니다 · 새 값 입력 시 교체"
                    if selected_provider == snapshot.provider_id
                    and snapshot.llm_configured
                    else "API Key 입력"
                ),
                help="기존 Key는 화면에 다시 표시하지 않습니다. 빈 칸은 기존 값을 유지합니다.",
                key="mpt_easy_setup_llm_api_key",
            )

        pexels_api_key = st.text_input(
            "Pexels API Key",
            value="",
            type="password",
            placeholder=(
                "저장된 Key가 있습니다 · 새 값 입력 시 교체"
                if snapshot.pexels_configured
                else "Pexels API Key 입력"
            ),
            help="영상 소재 검색에 사용합니다. 기존 Key는 화면에 다시 표시하지 않습니다.",
            key="mpt_easy_setup_pexels_api_key",
        )
        st.caption(
            "입력한 Key는 MoneyPrinterTurbo의 기존 config.toml에 저장되며 "
            "MPT Easy가 별도 비밀 저장소를 만들지 않습니다."
        )

        save_col, test_col = st.columns(2)
        with save_col:
            save_clicked = st.button(
                "설정 저장",
                use_container_width=True,
                key="mpt_easy_setup_save",
            )
        with test_col:
            test_clicked = st.button(
                "저장 후 연결 확인",
                type="primary",
                use_container_width=True,
                key="mpt_easy_setup_test",
            )

        if save_clicked or test_clicked:
            try:
                save_result = save_easy_setup(
                    provider_id=selected_provider,
                    llm_api_key=llm_api_key,
                    pexels_api_key=pexels_api_key,
                    ollama_model_name=ollama_model_name,
                )
            except EasySetupError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"설정을 저장하지 못했습니다: {safe_exception_label(exc)}")
            else:
                if save_result.saved_immediately:
                    st.success("설정을 저장했습니다.")
                else:
                    st.info(
                        "현재 영상 작업이 설정을 사용 중이어서 저장을 예약했습니다. "
                        "작업이 끝나면 자동으로 반영됩니다."
                    )

                if test_clicked and save_result.saved_immediately:
                    with st.spinner("AI 모델과 Pexels 연결을 확인하는 중입니다..."):
                        connection_results = check_easy_connections()
                    for result in connection_results:
                        _render_connection_result(result)


_STEP_ICON = {
    EasyStepState.PENDING: "⏳",
    EasyStepState.ACTIVE: "🔄",
    EasyStepState.COMPLETE: "✅",
    EasyStepState.FAILED: "❌",
}


def _render_progress_steps(snapshot: EasyTaskSnapshot) -> None:
    for step in snapshot.steps:
        icon = _STEP_ICON[step.state]
        if step.state == EasyStepState.ACTIVE:
            detail = "진행 중"
        elif step.state == EasyStepState.COMPLETE:
            detail = "완료"
        elif step.state == EasyStepState.FAILED:
            detail = "문제 발생"
        else:
            detail = "대기"
        st.markdown(f"{icon} **{step.label_ko}** · {detail}")


def _render_completed_videos(snapshot: EasyTaskSnapshot) -> None:
    safe_videos = safe_result_video_paths(snapshot.task_id, snapshot.videos)
    if not safe_videos:
        st.warning(
            "작업은 완료되었지만 현재 세션에서 결과 영상 파일을 찾지 못했습니다. "
            "기존 고급 WebUI의 작업 목록에서도 결과를 확인할 수 있습니다."
        )
        return

    st.success("🎉 영상이 완성되었습니다.")
    if snapshot.warnings:
        st.warning("영상은 완성되었지만 일부 부가 기능에서 경고가 발생했습니다.")
        with st.expander("경고 상세 보기", expanded=False):
            for warning in snapshot.warnings:
                st.write(redact_sensitive_text(warning))

    for index, video_path in enumerate(safe_videos, start=1):
        if len(safe_videos) > 1:
            st.markdown(f"**결과 영상 {index}**")
        st.video(str(video_path))
        with video_path.open("rb") as video_file:
            st.download_button(
                "MP4 저장" if len(safe_videos) == 1 else f"MP4 저장 {index}",
                data=video_file,
                file_name=video_path.name,
                mime=mimetypes.guess_type(video_path.name)[0] or "video/mp4",
                key=f"mpt_easy_download_{snapshot.task_id}_{index}",
                use_container_width=True,
            )


def _render_task_snapshot(snapshot: EasyTaskSnapshot) -> None:
    st.subheader("영상 제작 진행", divider="gray")
    st.caption(f"작업 ID: {snapshot.task_id}")

    if snapshot.state == EasyTaskState.WAITING:
        st.info("영상 생성 작업이 접수되는 중입니다.")
        st.progress(0, text="0% · 작업 접수 확인 중")
        _render_progress_steps(snapshot)
        return

    if snapshot.state == EasyTaskState.PROCESSING:
        st.info(f"현재 단계: {snapshot.current_stage_ko}")
        st.progress(
            snapshot.progress,
            text=f"{snapshot.progress}% · {snapshot.current_stage_ko}",
        )
        _render_progress_steps(snapshot)
        return

    if snapshot.state == EasyTaskState.FAILED:
        st.error(f"{snapshot.current_stage_ko} 단계에서 영상 제작을 완료하지 못했습니다.")
        _render_progress_steps(snapshot)
        if snapshot.error:
            with st.expander("오류 상세 보기", expanded=False):
                st.code(redact_sensitive_text(snapshot.error))
        st.caption("설정을 확인한 뒤 다시 시도해 주세요. 기존 고급 WebUI에서도 같은 작업 상태를 확인할 수 있습니다.")
        return

    st.progress(100, text="100% · 영상 완성")
    _render_progress_steps(snapshot)
    _render_completed_videos(snapshot)


@st.fragment(run_every=1.0)
def _render_running_task(task_id: str) -> None:
    """Poll canonical task state only while the Easy generation is active."""

    try:
        snapshot = get_easy_task_snapshot(task_id)
    except Exception as exc:
        st.error(f"영상 제작 상태를 불러오지 못했습니다: {safe_exception_label(exc)}")
        return

    if snapshot.terminal:
        st.rerun(scope="app")
    _render_task_snapshot(snapshot)


def _render_current_task(task_id: str) -> None:
    try:
        snapshot = get_easy_task_snapshot(task_id)
    except Exception as exc:
        st.error(f"영상 제작 상태를 불러오지 못했습니다: {safe_exception_label(exc)}")
        return

    if snapshot.terminal:
        _render_task_snapshot(snapshot)
    else:
        _render_running_task(task_id)


st.markdown(
    """
    <div class="mpt-hero">
      <h1>🎬 MPT Easy</h1>
      <div class="mpt-muted">복잡한 설정은 숨기고, 필요한 것만 골라 쇼츠를 만듭니다.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("v0.1 · Easy 화면은 기존 MoneyPrinterTurbo 생성 엔진을 그대로 사용합니다.")

_render_easy_setup()

st.divider()

topic = st.text_area(
    "영상 주제",
    placeholder="예: 여름철 전기요금을 줄이는 5가지 방법",
    height=110,
    help="한 문장만 입력해도 됩니다. 자세히 적을수록 스크립트 생성 방향이 명확해집니다.",
)

st.subheader("콘텐츠 유형", divider="gray")
content_value = st.radio(
    "콘텐츠 유형 선택",
    options=[preset.value for preset in EasyContentPreset],
    index=0,
    format_func=content_label,
    horizontal=True,
    label_visibility="collapsed",
)
selected_content = CONTENT_PRESETS[EasyContentPreset(content_value)]
st.caption(selected_content.description_ko)

st.subheader("영상 길이", divider="gray")
duration_value = st.radio(
    "영상 길이 선택",
    options=[duration.value for duration in EasyDuration],
    index=1,
    format_func=duration_label,
    horizontal=True,
    label_visibility="collapsed",
)
selected_duration = DURATION_PROFILES[EasyDuration(duration_value)]
st.caption(
    f"{selected_duration.description_ko} · 최종 영상 길이를 정확한 초 단위로 보장하는 설정은 아닙니다."
)

voice_id = st.selectbox(
    "음성",
    options=[option.voice_id for option in VOICE_OPTIONS],
    index=0,
    format_func=voice_label,
    help="v0.1에서는 별도 API 키가 필요 없는 기본 Edge/Azure V1 계열의 한국어 음성만 노출합니다.",
)

with st.expander("⚙️ 고급 설정", expanded=False):
    aspect_value = st.radio(
        "화면 비율",
        options=[option.aspect.value for option in ASPECT_OPTIONS],
        index=0,
        format_func=aspect_label,
        horizontal=True,
    )
    selected_aspect = next(
        option for option in ASPECT_OPTIONS if option.aspect.value == aspect_value
    )
    st.caption(selected_aspect.description_ko)
    st.caption("더 많은 세부 옵션은 기존 MoneyPrinterTurbo 고급 WebUI에서 계속 사용할 수 있습니다.")

st.divider()

if st.button("영상 만들기", type="primary", use_container_width=True):
    st.session_state.pop("mpt_easy_task_id", None)
    try:
        params = build_params_from_ui(
            topic,
            content_preset=content_value,
            duration=duration_value,
            aspect=aspect_value,
            voice_id=voice_id,
        )
        st.session_state["mpt_easy_video_params"] = params.model_dump(mode="json")
        submission = submit_easy_generation(params)
    except (EasyPresetError, ValueError) as exc:
        st.error(str(exc))
    except EasyGenerationNotReady:
        st.error("영상 제작 준비가 아직 끝나지 않았습니다.")
    except Exception as exc:
        st.error(f"영상 생성 작업을 시작하지 못했습니다: {safe_exception_label(exc)}")
    else:
        st.session_state["mpt_easy_task_id"] = submission.task_id
        st.success("영상 생성 작업을 시작했습니다.")
        st.caption(f"작업 ID: {submission.task_id}")

saved_params = st.session_state.get("mpt_easy_video_params")
if saved_params:
    params = VideoParams(**saved_params)
    st.subheader("적용 설정", divider="gray")
    summary = summarize_params(params)
    left, right = st.columns(2)
    items = list(summary.items())
    for index, (label, value) in enumerate(items):
        target = left if index % 2 == 0 else right
        with target:
            rendered = "켜짐" if value is True else "꺼짐" if value is False else value
            st.metric(label, rendered)

    # Re-evaluate against current runtime config so returning from the advanced
    # settings screen immediately reflects newly entered API keys.
    readiness = check_generation_readiness(params)
    _render_readiness(readiness)

    with st.expander("개발자용 VideoParams 확인", expanded=False):
        st.json(saved_params)

current_task_id = st.session_state.get("mpt_easy_task_id")
if current_task_id:
    _render_current_task(current_task_id)
