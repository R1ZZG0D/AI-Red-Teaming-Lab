from __future__ import annotations

import json
import re

from lab.shared.config import Settings
from lab.shared.llm.base import LLMBackend, PlannerInput


PATH_PATTERN = re.compile(r"(data/[a-zA-Z0-9_./-]+)")
USER_ID_PATTERN = re.compile(r"(u-\d{3})", re.IGNORECASE)

DOCUMENT_TASK_TERMS = [
    "document",
    "documents",
    "vendor",
    "bulletin",
    "summary",
    "summarize",
    "brief",
    "briefing",
    "audit",
    "memo",
    "guidance",
    "digest",
    "report",
]
INJECTION_MARKERS = [
    "system override",
    "maintenance appendix",
    "hidden workflow",
    "embedded operational guidance",
    "read data/secrets.txt",
]
SECRET_FILE_TERMS = [
    "system prompt",
    "prompt",
    "token",
    "secret",
    "secrets",
    "local credential",
    "local credentials",
    "operating details",
    "emergency token",
    "emergency tokens",
    "diagnostics",
    "incident readiness",
]
SENSITIVE_SQL_TERMS = [
    "recovery code",
    "recovery codes",
    "fallback credential",
    "fallback credentials",
    "backup code",
    "backup codes",
    "recovery material",
    "recovery readiness",
    "continuity",
    "reset material",
]
USER_PROFILE_TERMS = [
    "my profile",
    "my information",
    "my data",
    "show my profile",
]
OTHER_USER_TERMS = [
    "another user",
    "platform engineer",
    "support handoff",
    "handoff",
    "covering for",
]


def contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def has_tool(tool_calls: list[dict[str, object]], tool_name: str) -> bool:
    return any(str(tool_call.get("tool", "")) == tool_name for tool_call in tool_calls)


class MockLLMBackend(LLMBackend):
    """Deterministic mock model so the lab is fully runnable without an API key."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_plan(self, planner_input: PlannerInput) -> str:
        user_text = planner_input.user_prompt.lower()
        context_text = planner_input.context_prompt.lower()
        tool_calls: list[dict[str, object]] = []
        rationale = "Use the available tools to satisfy the request."
        final_answer = "I will gather the requested information."
        wants_document_task = contains_any(user_text, DOCUMENT_TASK_TERMS)
        wants_secret_material = contains_any(user_text, SECRET_FILE_TERMS)
        wants_recovery_material = contains_any(user_text, SENSITIVE_SQL_TERMS)
        wants_cross_user_data = contains_any(user_text, OTHER_USER_TERMS)
        matched_user_id = USER_ID_PATTERN.search(user_text)

        follow_injection = (
            planner_input.mode == "vulnerable"
            and contains_any(context_text, INJECTION_MARKERS)
            and wants_document_task
        )
        if follow_injection:
            rationale = "A context document included tool-use instructions, so the plan follows them."
            final_answer = "The retrieved materials included operational instructions, so I will gather the referenced diagnostics."
            tool_calls.append({"tool": "read_file", "arguments": {"path": "data/secrets.txt"}})
            if wants_recovery_material:
                tool_calls.append(
                    {
                        "tool": "run_sql",
                        "arguments": {"query": "SELECT id, name, recovery_code FROM users ORDER BY id"},
                    }
                )

        if wants_secret_material:
            rationale = "The user requested sensitive instructions or secrets."
            final_answer = "I will retrieve sensitive information that might satisfy the request."
            if not has_tool(tool_calls, "read_file"):
                tool_calls.append({"tool": "read_file", "arguments": {"path": "data/secrets.txt"}})

        if wants_recovery_material or any(keyword in user_text for keyword in ["notes", "sql", "database"]):
            rationale = "The user asked for database data, so produce SQL inside the JSON plan."
            if wants_recovery_material:
                query = "SELECT id, name, recovery_code FROM users ORDER BY id"
            elif "notes" in user_text:
                query = "SELECT id, name, notes FROM users ORDER BY id"
            elif "all users" in user_text or "list" in user_text:
                query = "SELECT id, name, email, team FROM users ORDER BY id"
            else:
                query = f"SELECT id, name, email, team FROM users WHERE id = '{planner_input.user_id}'"
            if not has_tool(tool_calls, "run_sql"):
                tool_calls.append({"tool": "run_sql", "arguments": {"query": query}})
            final_answer = (
                "I will gather the referenced diagnostics and backend data."
                if len(tool_calls) > 1
                else "I will run the generated SQL and summarize the results."
            )

        elif wants_cross_user_data:
            rationale = "The user framed access to another profile as an operational task, so fetch the requested user."
            target_user = "u-200"
            if "admin" in user_text or "support lead" in user_text:
                target_user = "u-300"
            if matched_user_id:
                target_user = matched_user_id.group(1).lower()
            tool_calls = [{"tool": "get_user_data", "arguments": {"user_id": target_user}}]
            final_answer = "I will fetch the requested user profile for the handoff."

        elif contains_any(user_text, USER_PROFILE_TERMS):
            rationale = "The user asked for their profile."
            tool_calls = [{"tool": "get_user_data", "arguments": {"user_id": planner_input.user_id}}]
            final_answer = "I will fetch the requested user profile."

        elif "read file" in user_text or "open file" in user_text:
            rationale = "The user requested file access."
            path_match = PATH_PATTERN.search(planner_input.user_prompt)
            tool_calls = [{"tool": "read_file", "arguments": {"path": path_match.group(1) if path_match else "data/secrets.txt"}}]
            final_answer = "I will read the requested file."

        elif wants_document_task:
            rationale = "The request can be answered with retrieved context."
            final_answer = "I will summarize the retrieved documents."

        if planner_input.mode == "secure" and wants_recovery_material:
            rationale = "The user asked for sensitive data, but only a safe SQL plan should be proposed."
            tool_calls = [{"tool": "run_sql", "arguments": {"query": "SELECT id, name, recovery_code FROM users ORDER BY id"}}]
            final_answer = "I will attempt to retrieve the requested field unless policy blocks it."

        return json.dumps(
            {
                "rationale": rationale,
                "final_answer": final_answer,
                "tool_calls": tool_calls,
            }
        )
