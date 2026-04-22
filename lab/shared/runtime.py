from __future__ import annotations

import json
from typing import Any

from lab.shared.schemas import ChatRequest, ToolCallRecord


def stringify_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [stringify_value(item) for item in value]
        parts = [part for part in parts if part]
        return "\n".join(parts)
    if isinstance(value, dict):
        for key in ("text", "content", "final_answer", "answer", "message", "response"):
            if key in value:
                text = stringify_value(value[key])
                if text:
                    return text
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def normalize_tool_calls(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tool = stringify_value(item.get("tool"))
        arguments = item.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}
        if tool:
            normalized.append({"tool": tool, "arguments": arguments})
    return normalized


def parse_llm_output(raw_output: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return {
            "rationale": "The raw output was not valid JSON.",
            "final_answer": raw_output,
            "tool_calls": [],
        }
    if not isinstance(parsed, dict):
        return {
            "rationale": "The raw output decoded successfully but was not a JSON object.",
            "final_answer": stringify_value(parsed),
            "tool_calls": [],
        }
    return {
        "rationale": stringify_value(parsed.get("rationale")),
        "final_answer": stringify_value(parsed.get("final_answer")),
        "tool_calls": normalize_tool_calls(parsed.get("tool_calls")),
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
    final_answer = stringify_value(plan.get("final_answer"))
    if final_answer:
        lines.append(final_answer)
        if successful and "fetch the requested user profile" in final_answer.lower():
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
