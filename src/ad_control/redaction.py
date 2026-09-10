from __future__ import annotations

import re
from typing import Any

_SECRET_WORDS = (
    "authorization", "cookie", "token", "password", "passwd", "secret",
    "api_key", "apikey", "credential", "private_key",
)
_SECRET_KEY = (
    r"[A-Za-z0-9_-]*(?:authorization|cookie|token|password|passwd|secret|"
    r"api[_-]?key|credential|private[_-]?key)[A-Za-z0-9_-]*"
)
_STRING_SECRET_PATTERNS = (
    # JSON-like or key/value text with a quoted value.
    re.compile(rf"(?i)([\"']?{_SECRET_KEY}[\"']?\s*[:=]\s*)([\"'])(.*?)(\2)"),
    # Header/log text with an unquoted value.
    re.compile(rf"(?i)(\b{_SECRET_KEY}\b\s*[:=]\s*)([^,;\s}}]+)"),
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")


def _redact_string(value: str) -> str:
    value = _BEARER_PATTERN.sub("Bearer ***REDACTED***", value)
    for pattern in _STRING_SECRET_PATTERNS:
        value = pattern.sub(r"\1\2***REDACTED***\4" if pattern.groups == 4 else r"\1***REDACTED***", value)
    return value


def redact(value: Any, key: str = "") -> Any:
    """??????????????"""
    lower_key = key.lower().replace("-", "_")
    if any(word in lower_key for word in _SECRET_WORDS):
        return "***REDACTED***"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact(item, key) for item in value]
    if isinstance(value, str):
        return _redact_string(value)
    return value
