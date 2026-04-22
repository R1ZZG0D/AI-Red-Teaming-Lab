from __future__ import annotations

from pathlib import Path
from typing import Any

from lab.shared.config import Settings
from lab.shared.database import execute_sql, lookup_user
from lab.shared.schemas import ToolCallRecord


class VulnerableToolExecutor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolCallRecord:
        try:
            if tool_name == "run_sql":
                # Vulnerable by design: execute whatever SQL the model produced without validation.
                result = execute_sql(self.settings.db_path, str(arguments.get("query", "")))
            elif tool_name == "read_file":
                # Vulnerable by design: resolve user/model supplied paths without any sandbox or allowlist.
                result = self._read_unrestricted_file(str(arguments.get("path", "")))
            elif tool_name == "get_user_data":
                # Vulnerable by design: allow arbitrary user_id access with no role or ownership check.
                result = lookup_user(self.settings.db_path, str(arguments.get("user_id", "")))
            else:
                return ToolCallRecord(
                    tool=tool_name,
                    arguments=arguments,
                    status="failed",
                    reason="Unknown tool requested by the model.",
                )
            return ToolCallRecord(tool=tool_name, arguments=arguments, status="completed", result=result)
        except Exception as exc:
            return ToolCallRecord(
                tool=tool_name,
                arguments=arguments,
                status="failed",
                reason=str(exc),
            )

    def _read_unrestricted_file(self, raw_path: str) -> str:
        path = Path(raw_path)
        if not path.is_absolute():
            path = self.settings.base_dir / raw_path
        return path.read_text(encoding="utf-8")

