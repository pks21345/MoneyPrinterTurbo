import unittest
from unittest.mock import Mock

import requests

from webui.easy.setup import (
    NOOP_CONNECTION_LOCK,
    PROVIDER_CHOICES,
    EasySetupError,
    build_easy_setup_updates,
    get_easy_setup_snapshot,
    save_easy_setup,
    check_easy_connections,
    check_pexels_connection,
)


class EasySetupTests(unittest.TestCase):
    def test_provider_choices_are_unique_and_small(self):
        ids = [choice.provider_id for choice in PROVIDER_CHOICES]
        self.assertEqual(ids, ["moonshot", "openai", "gemini", "ollama"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_snapshot_exposes_status_not_secret_values(self):
        snapshot = get_easy_setup_snapshot(
            {
                "llm_provider": "openai",
                "openai_api_key": "secret-openai",
                "openai_model_name": "",
                "openai_base_url": "",
                "pexels_api_keys": ["secret-pexels"],
            }
        )

        self.assertTrue(snapshot.ready)
        self.assertTrue(snapshot.llm_configured)
        self.assertTrue(snapshot.pexels_configured)
        self.assertNotIn("secret", repr(snapshot))

    def test_blank_secret_inputs_preserve_existing_secrets(self):
        current = {
            "llm_provider": "openai",
            "openai_api_key": "existing-openai",
            "pexels_api_keys": ["existing-pexels"],
        }
        updates = build_easy_setup_updates(
            provider_id="openai",
            llm_api_key="",
            pexels_api_key="",
            current_config=current,
        )

        self.assertEqual(updates, {"llm_provider": "openai"})

    def test_new_secrets_are_written_only_to_selected_fields(self):
        updates = build_easy_setup_updates(
            provider_id="gemini",
            llm_api_key="  gemini-new  ",
            pexels_api_key="  pexels-new  ",
            current_config={},
        )

        self.assertEqual(updates["llm_provider"], "gemini")
        self.assertEqual(updates["gemini_api_key"], "gemini-new")
        self.assertEqual(updates["pexels_api_keys"], ["pexels-new"])
        self.assertNotIn("openai_api_key", updates)

    def test_ollama_model_is_saved_without_api_key(self):
        updates = build_easy_setup_updates(
            provider_id="ollama",
            ollama_model_name=" qwen3:8b ",
            current_config={},
        )

        self.assertEqual(updates["ollama_model_name"], "qwen3:8b")
        self.assertNotIn("ollama_api_key", updates)

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(EasySetupError):
            build_easy_setup_updates(provider_id="unknown", current_config={})

    def test_save_uses_canonical_config_update_and_save_hooks(self):
        section = {
            "llm_provider": "moonshot",
            "openai_api_key": "",
            "pexels_api_keys": [],
        }
        updates = []

        def updater(target, key, value):
            updates.append((key, value))
            target[key] = value
            return True

        save_mock = Mock(return_value=True)
        result = save_easy_setup(
            provider_id="openai",
            llm_api_key="openai-key",
            pexels_api_key="pexels-key",
            config_section=section,
            update_func=updater,
            save_func=save_mock,
        )

        self.assertTrue(result.saved_immediately)
        self.assertIn(("llm_provider", "openai"), updates)
        self.assertIn(("openai_api_key", "openai-key"), updates)
        self.assertIn(("pexels_api_keys", ["pexels-key"]), updates)
        save_mock.assert_called_once_with()

    def test_connection_tests_do_not_run_when_settings_are_missing(self):
        llm_tester = Mock()
        pexels_tester = Mock()
        results = check_easy_connections(
            app_config={"llm_provider": "moonshot", "pexels_api_keys": []},
            llm_tester=llm_tester,
            pexels_tester=pexels_tester,
            lock_factory=NOOP_CONNECTION_LOCK,
        )

        self.assertFalse(results[0].success)
        self.assertFalse(results[1].success)
        llm_tester.assert_not_called()
        pexels_tester.assert_not_called()

    def test_connection_tests_use_saved_values_without_returning_secrets(self):
        llm_tester = Mock(return_value=(True, "", 0.12))
        pexels_tester = Mock(return_value=(True, "Pexels API 연결에 성공했습니다.", 0.2))
        results = check_easy_connections(
            app_config={
                "llm_provider": "openai",
                "openai_api_key": "secret-openai",
                "openai_model_name": "",
                "openai_base_url": "",
                "pexels_api_keys": ["secret-pexels"],
            },
            llm_tester=llm_tester,
            pexels_tester=pexels_tester,
            lock_factory=NOOP_CONNECTION_LOCK,
        )

        self.assertTrue(results[0].success)
        self.assertTrue(results[1].success)
        pexels_tester.assert_called_once_with("secret-pexels")
        self.assertNotIn("secret", repr(results))

    def test_busy_runtime_returns_neutral_results_without_network_calls(self):
        llm_tester = Mock()
        pexels_tester = Mock()
        results = check_easy_connections(
            app_config={
                "llm_provider": "openai",
                "openai_api_key": "key",
                "openai_model_name": "",
                "openai_base_url": "",
                "pexels_api_keys": ["pexels"],
            },
            llm_tester=llm_tester,
            pexels_tester=pexels_tester,
            lock_factory=lambda: __import__("contextlib").nullcontext(False),
        )

        self.assertIsNone(results[0].success)
        self.assertIsNone(results[1].success)
        llm_tester.assert_not_called()
        pexels_tester.assert_not_called()

    def check_pexels_connection_statuses_are_friendly(self):
        response = Mock(status_code=401)
        ok, detail, _ = check_pexels_connection(
            "pexels-secret",
            request_get=Mock(return_value=response),
        )
        self.assertFalse(ok)
        self.assertIn("API Key", detail)
        self.assertNotIn("pexels-secret", detail)

    def test_pexels_network_error_does_not_echo_secret(self):
        request_get = Mock(side_effect=requests.ConnectionError("network down"))
        ok, detail, _ = check_pexels_connection(
            "pexels-secret",
            request_get=request_get,
        )

        self.assertFalse(ok)
        self.assertIn("ConnectionError", detail)
        self.assertNotIn("pexels-secret", detail)


if __name__ == "__main__":
    unittest.main()
