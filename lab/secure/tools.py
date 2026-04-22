from __future__ import annotations

from pathlib import Path
from typing import Any

from lab.shared.config import Settings
from lab.shared.database import execute_sql, lookup_user
from lab.shared.schemas import ToolCallRecord
from lab.secure.validators import redact_result


class SecureToolExecutor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        resolved_path: Path | None = None,
        request_role: str | None = None,
    ) -> ToolCallRecord:
        try:
            if tool_name == "run_sql":
                # Guardrail: this is only reached after SQL allowlist checks, so unsafe statements never execute.
                result = redact_result(execute_sql(self.settings.db_path, str(arguments.get("query", ""))), self.settings)
            elif tool_name == "read_file":
                # Guardrail: resolved_path is validated to stay inside the sample document directory.
                result = redact_result(resolved_path.read_text(encoding="utf-8"), self.settings) if resolved_path else ""
            elif tool_name == "get_user_data":
                # Guardrail: ownership and role checks happen before lookup, then the result is redacted for output safety.
                raw_result = lookup_user(self.settings.db_path, str(arguments.get("user_id", "")))
                if raw_result and request_role == "student":
                    raw_result.pop("notes", None)
                result = redact_result(raw_result, self.settings)
            else:
                return ToolCallRecord(
                    tool=tool_name,
                    arguments=arguments,
                    status="blocked",
                    reason="Unknown tool blocked by secure executor.",
                )
            return ToolCallRecord(tool=tool_name, arguments=arguments, status="completed", result=result)
        except Exception as exc:
            return ToolCallRecord(tool=tool_name, arguments=arguments, status="failed", reason=str(exc))
