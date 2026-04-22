from __future__ import annotations

import json
from typing import Any

from lab.shared.schemas import ChatRequest, ToolCallRecord


def parse_llm_output(raw_output: str) -> dict[str, Any]:
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return {
            "rationale": "The raw output was not valid JSON.",
            "final_answer": raw_output,
            "tool_calls": [],
        }


def render_tool_result(tool_name: str, result: Any) -> str:
    if result is None:
        return f"{tool_name}: no result"
    return f"{tool_name}: {json.dumps(result, indent=2, ensure_ascii=True)}"


def summarize_successful_tool_result(record: ToolCallRecord) -> str | None:
    if record.tool == "get_user_data" and isinstance(record.result, dict):
        name = record.result.get("name")
        email = record.result.get("email")
        team = record.result.get("team")
        role = record.result.get("role")
        if name and email and team and role:
            return f"{name} ({email}) is on the {team} team with role {role}."
    return None


def compose_answer(request: ChatRequest, plan: dict[str, Any], tool_calls: list[ToolCallRecord], fallback: str) -> str:
    successful = [record for record in tool_calls if record.status == "completed"]
    blocked = [record for record in tool_calls if record.status == "blocked"]
    failed = [record for record in tool_calls if record.status == "failed"]
    lines: list[str] = []
    if plan.get("final_answer"):
        lines.append(plan["final_answer"])
        if successful and "fetch the requested user profile" in str(plan["final_answer"]).lower():
            summary = summarize_successful_tool_result(successful[0])
            if summary:
                lines.append(summary)
    elif blocked:
        lines.append("I cannot complete that request in the secure environment.")
    elif failed:
        lines.append("I tried to complete that request, but the operation failed.")
    if not lines:
        lines.append(fallback)
    return "\n\n".join(lines)
