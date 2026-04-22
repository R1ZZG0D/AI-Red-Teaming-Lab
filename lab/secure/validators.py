from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from lab.shared.config import Settings
from lab.shared.schemas import StrictLLMPlan


UNSAFE_SQL_PATTERNS = [
    re.compile(r"\b(update|delete|insert|drop|alter|attach|pragma|union)\b", re.IGNORECASE),
    re.compile(r"--"),
    re.compile(r"/\*"),
    re.compile(r";\s*\S"),
]
ALLOWED_COLUMNS = {"id", "name", "email", "team", "role"}
DISALLOWED_COLUMNS = {"notes", "recovery_code"}


def validate_plan(raw_output: str) -> tuple[StrictLLMPlan | None, str | None]:
    try:
        plan = StrictLLMPlan.model_validate_json(raw_output)
    except ValidationError as exc:
        return None, str(exc)
    return plan, None


def validate_sql(query: str) -> tuple[bool, str]:
    normalized = " ".join(query.strip().split())
    if not normalized.lower().startswith("select "):
        return False, "Only SELECT statements are allowed."
    if any(pattern.search(normalized) for pattern in UNSAFE_SQL_PATTERNS):
        return False, "Unsafe SQL keyword or comment pattern detected."
    if "*" in normalized:
        return False, "Wildcard selection is not allowed."

    match = re.match(
        r"(?is)^select\s+(?P<columns>.+?)\s+from\s+(?P<table>[a-z_]+)(?:\s+where\s+.+)?(?:\s+order\s+by\s+.+)?(?:\s+limit\s+\d+)?$",
        normalized,
    )
    if not match:
        return False, "Only simple single-table SELECT queries are allowed."
    if match.group("table").lower() != "users":
        return False, "Only the users table is allowlisted."

    raw_columns = [column.strip().split()[-1].lower() for column in match.group("columns").split(",")]
    if any(column in DISALLOWED_COLUMNS for column in raw_columns):
        return False, "Sensitive columns are blocked."
    if not all(column in ALLOWED_COLUMNS for column in raw_columns):
        return False, "Query requested a column outside the allowlist."
    return True, "SQL passed validation."


def validate_file_path(settings: Settings, raw_path: str) -> tuple[Path | None, str | None]:
    path = Path(raw_path)
    if not path.is_absolute():
        path = settings.base_dir / raw_path
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError:
        return None, "Requested file does not exist."
    documents_root = settings.documents_dir.resolve()
    if not str(resolved).startswith(str(documents_root)):
        return None, "File access is restricted to the sample document directory."
    if resolved.name == settings.secrets_file.name:
        return None, "Secret files are never allowlisted."
    return resolved, None


def redact_sensitive_text(text: str, settings: Settings) -> str:
    redacted = text.replace(settings.system_prompt_secret, "[REDACTED]")
    redacted = redacted.replace(settings.emergency_token, "[REDACTED]")
    redacted = re.sub(r"\b[a-z]+-\d{4}\b", "[REDACTED-RECOVERY-CODE]", redacted, flags=re.IGNORECASE)
    redacted = redacted.replace("sk-lab-demo-key", "[REDACTED]")
    return redacted


def redact_result(result: Any, settings: Settings) -> Any:
    if isinstance(result, str):
        return redact_sensitive_text(result, settings)
    if isinstance(result, list):
        return [redact_result(item, settings) for item in result]
    if isinstance(result, dict):
        redacted = {}
        for key, value in result.items():
            if key == "recovery_code":
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_result(value, settings)
        return redacted
    return result

