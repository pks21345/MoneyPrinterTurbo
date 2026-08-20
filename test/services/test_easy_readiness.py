import unittest
from unittest.mock import Mock

from app.models.schema import VideoParams
from webui.easy.generation import EasyGenerationNotReady, submit_easy_generation
from webui.easy.readiness import check_generation_readiness


READY_CONFIG = {
    "llm_provider": "openai",
    "openai_api_key": "test-key",
    "openai_model_name": "",
    "openai_base_url": "",
    "pexels_api_keys": ["pexels-test-key"],
}


class EasyReadinessTests(unittest.TestCase):
    def test_default_easy_params_report_missing_llm_and_pexels_keys(self):
        params = VideoParams(video_subject="테스트 주제")
        report = check_generation_readiness(
            params,
            app_config={"llm_provider": "moonshot", "pexels_api_keys": []},
        )

        self.assertFalse(report.ready)
        blocker_codes = {check.code for check in report.blockers}
        self.assertEqual(blocker_codes, {"llm_provider", "video_material"})

    def test_registry_defaults_satisfy_model_and_base_url(self):
        params = VideoParams(video_subject="테스트 주제")
        report = check_generation_readiness(params, app_config=READY_CONFIG)

        self.assertTrue(report.ready)
        self.assertTrue(all(check.ready for check in report.checks))

    def test_local_source_requires_materials(self):
        params = VideoParams(video_subject="테스트", video_source="local")
        report = check_generation_readiness(params, app_config=READY_CONFIG)

        self.assertFalse(report.ready)
        material = next(check for check in report.checks if check.code == "video_material")
        self.assertFalse(material.ready)

    def test_ollama_does_not_require_api_key_or_static_base_url(self):
        params = VideoParams(video_subject="테스트")
        report = check_generation_readiness(
            params,
            app_config={
                "llm_provider": "ollama",
                "ollama_model_name": "qwen3:8b",
                "ollama_base_url": "",
                "pexels_api_keys": ["pexels-test-key"],
            },
        )

        llm_check = next(check for check in report.checks if check.code == "llm_provider")
        self.assertTrue(llm_check.ready)

    def test_submit_blocks_before_calling_engine_when_not_ready(self):
        submitter = Mock()
        params = VideoParams(video_subject="테스트")

        with self.assertRaises(EasyGenerationNotReady):
            submit_easy_generation(
                params,
                app_config={"llm_provider": "moonshot", "pexels_api_keys": []},
                submitter=submitter,
            )

        submitter.assert_not_called()

    def test_submit_calls_existing_engine_with_same_video_params(self):
        submitter = Mock()
        params = VideoParams(video_subject="테스트")

        result = submit_easy_generation(
            params,
            app_config=READY_CONFIG,
            submitter=submitter,
            task_id_factory=lambda: "easy-task-001",
        )

        self.assertEqual(result.task_id, "easy-task-001")
        submitter.assert_called_once()
        kwargs = submitter.call_args.kwargs
        self.assertEqual(kwargs["task_id"], "easy-task-001")
        self.assertEqual(kwargs["params"], params)
        self.assertIn("capture_logs", kwargs)


if __name__ == "__main__":
    unittest.main()
