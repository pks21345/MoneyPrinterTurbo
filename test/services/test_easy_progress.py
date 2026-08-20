import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from app.models import const
from webui.easy.progress import (
    EasyStepState,
    EasyTaskState,
    build_easy_task_snapshot,
    get_easy_task_snapshot,
    safe_result_video_paths,
)


class EasyProgressTests(unittest.TestCase):
    def test_missing_task_is_waiting(self):
        snapshot = build_easy_task_snapshot("task-1", None)

        self.assertEqual(snapshot.state, EasyTaskState.WAITING)
        self.assertEqual(snapshot.progress, 0)
        self.assertEqual(snapshot.current_stage_ko, "작업 접수 확인 중")
        self.assertTrue(
            all(step.state == EasyStepState.PENDING for step in snapshot.steps)
        )

    def test_processing_progress_maps_to_real_pipeline_stage(self):
        snapshot = build_easy_task_snapshot(
            "task-1",
            {"state": const.TASK_STATE_PROCESSING, "progress": 30},
        )

        self.assertEqual(snapshot.state, EasyTaskState.PROCESSING)
        self.assertEqual(snapshot.current_stage_ko, "자막 생성")
        step_states = {step.key: step.state for step in snapshot.steps}
        self.assertEqual(step_states["script"], EasyStepState.COMPLETE)
        self.assertEqual(step_states["terms"], EasyStepState.COMPLETE)
        self.assertEqual(step_states["audio"], EasyStepState.COMPLETE)
        self.assertEqual(step_states["subtitle"], EasyStepState.ACTIVE)
        self.assertEqual(step_states["materials"], EasyStepState.PENDING)

    def test_progress_is_clamped(self):
        snapshot = build_easy_task_snapshot(
            "task-1",
            {"state": const.TASK_STATE_PROCESSING, "progress": 999},
        )
        self.assertEqual(snapshot.progress, 100)

    def test_failed_stage_is_localized_and_marked(self):
        snapshot = build_easy_task_snapshot(
            "task-1",
            {
                "state": const.TASK_STATE_FAILED,
                "progress": 40,
                "failed_stage": "materials",
                "error": "provider unavailable",
            },
        )

        self.assertEqual(snapshot.state, EasyTaskState.FAILED)
        self.assertEqual(snapshot.current_stage_ko, "영상 소재 준비")
        material = next(step for step in snapshot.steps if step.key == "materials")
        self.assertEqual(material.state, EasyStepState.FAILED)
        self.assertEqual(snapshot.error, "provider unavailable")

    def test_complete_task_forces_100_and_keeps_results(self):
        snapshot = build_easy_task_snapshot(
            "task-1",
            {
                "state": const.TASK_STATE_COMPLETE,
                "progress": 50,
                "videos": ["/tmp/a.mp4", "/tmp/b.mp4"],
                "warnings": [{"code": "fallback"}],
            },
        )

        self.assertEqual(snapshot.state, EasyTaskState.COMPLETE)
        self.assertEqual(snapshot.progress, 100)
        self.assertEqual(snapshot.current_stage_ko, "영상 완성")
        self.assertEqual(snapshot.videos, ("/tmp/a.mp4", "/tmp/b.mp4"))
        self.assertTrue(
            all(step.state == EasyStepState.COMPLETE for step in snapshot.steps)
        )

    def test_get_snapshot_uses_injected_task_getter(self):
        getter = Mock(
            return_value={"state": const.TASK_STATE_PROCESSING, "progress": 20}
        )

        snapshot = get_easy_task_snapshot("task-abc", task_getter=getter)

        getter.assert_called_once_with("task-abc")
        self.assertEqual(snapshot.current_stage_ko, "음성 생성")

    def test_safe_result_paths_stay_inside_exact_task_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task_dir = root / "task-1"
            task_dir.mkdir()
            safe_video = task_dir / "final.mp4"
            safe_video.write_bytes(b"video")
            sibling_dir = root / "task-2"
            sibling_dir.mkdir()
            sibling_video = sibling_dir / "other.mp4"
            sibling_video.write_bytes(b"other")
            outside = root.parent / "outside.mp4"
            outside.write_bytes(b"outside")
            try:
                result = safe_result_video_paths(
                    "task-1",
                    [str(safe_video), str(sibling_video), str(outside)],
                    task_root=root,
                )
            finally:
                outside.unlink(missing_ok=True)

        self.assertEqual(result, (safe_video.resolve(),))

    def test_path_traversal_task_id_returns_no_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = safe_result_video_paths(
                "../escape",
                [str(root / "anything.mp4")],
                task_root=root,
            )
        self.assertEqual(result, ())


if __name__ == "__main__":
    unittest.main()
