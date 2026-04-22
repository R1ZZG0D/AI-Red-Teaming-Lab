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


def compose_answer(request: ChatRequest, plan: dict[str, Any], tool_calls: list[ToolCallRecord], fallback: str) -> str:
    successful = [record for record in tool_calls if record.status == "completed"]
    blocked = [record for record in tool_calls if record.status == "blocked"]
    failed = [record for record in tool_calls if record.status == "failed"]
    lines: list[str] = []
    if plan.get("final_answer"):
        lines.append(plan["final_answer"])
    if successful:
        lines.append("Tool results:")
        for record in successful:
            lines.append(render_tool_result(record.tool, record.result))
    if blocked:
        lines.append("Blocked actions:")
        for record in blocked:
            lines.append(f"{record.tool}: {record.reason}")
    if failed:
        lines.append("Failed actions:")
        for record in failed:
            lines.append(f"{record.tool}: {record.reason}")
    if not lines:
        lines.append(fallback)
    return "\n\n".join(lines)

