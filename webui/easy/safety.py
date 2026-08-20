"""Small display-safety helpers for the MPT Easy UI."""

from __future__ import annotations

import re
from typing import Any

_AUTHORIZATION_RE = re.compile(
    r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?([^\s,;]+)"
)
_NAMED_SECRET_RE = re.compile(
    r"(?i)((?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|token|password|secret)"
    r"[\s\"']*[:=][\s\"']*)([^\s\"',;}]+)"
)
_PREFIX_SECRET_RE = re.compile(
    r"\b(?:sk|rk|pk|pplx|xai)-[A-Za-z0-9._-]{8,}\b"
)
_GOOGLE_KEY_RE = re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b")


def redact_sensitive_text(value: Any, *, max_length: int = 2000) -> str:
    """Return user-displayable text with common credential shapes removed."""

    text = str(value or "")
    text = _AUTHORIZATION_RE.sub(
        lambda match: f"{match.group(1)}{match.group(2) or ''}<redacted>", text
    )
    text = _NAMED_SECRET_RE.sub(lambda match: f"{match.group(1)}<redacted>", text)
    text = _PREFIX_SECRET_RE.sub("<redacted>", text)
    text = _GOOGLE_KEY_RE.sub("<redacted>", text)

    if max_length > 0 and len(text) > max_length:
        return text[:max_length].rstrip() + "…"
    return text


def safe_exception_label(exc: BaseException) -> str:
    """Expose only the exception type for unexpected UI-level failures."""

    return type(exc).__name__
