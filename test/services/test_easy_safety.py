import unittest

from webui.easy.safety import redact_sensitive_text, safe_exception_label


class TestEasySafety(unittest.TestCase):
    def test_redacts_authorization_bearer_header(self):
        text = redact_sensitive_text("Authorization: Bearer super-secret-token")
        self.assertNotIn("super-secret-token", text)
        self.assertIn("<redacted>", text)

    def test_redacts_named_api_key(self):
        text = redact_sensitive_text("api_key=sk-example123456789")
        self.assertNotIn("sk-example123456789", text)
        self.assertIn("<redacted>", text)

    def test_redacts_quoted_config_secret(self):
        text = redact_sensitive_text("'openai_api_key': 'sk-example123456789'")
        self.assertNotIn("sk-example123456789", text)

    def test_redacts_google_key_shape(self):
        key = "AIza" + "A" * 32
        text = redact_sensitive_text(f"provider rejected {key}")
        self.assertNotIn(key, text)

    def test_redacts_common_prefixed_key_shape(self):
        key = "sk-abcdefghijklmnopqrstuvwxyz"
        text = redact_sensitive_text(f"request failed for {key}")
        self.assertNotIn(key, text)

    def test_preserves_normal_error_message(self):
        text = redact_sensitive_text("HTTP 429: rate limit exceeded")
        self.assertEqual(text, "HTTP 429: rate limit exceeded")

    def test_truncates_very_long_detail(self):
        text = redact_sensitive_text("x" * 50, max_length=20)
        self.assertEqual(text, "x" * 20 + "…")

    def test_unexpected_exception_exposes_type_only(self):
        exc = RuntimeError("api_key=sk-should-never-render")
        self.assertEqual(safe_exception_label(exc), "RuntimeError")


if __name__ == "__main__":
    unittest.main()
