from __future__ import annotations

import json
import re

from lab.shared.challenges import challenge_by_id
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
    "appendix",
    "operational note",
]
INJECTION_MARKERS = [
    "system override",
    "maintenance appendix",
    "hidden workflow",
    "embedded operational guidance",
    "enpm604{vendor_bulletin_prompt_pivot}",
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
    "credential verification",
]
SENSITIVE_SQL_TERMS = [
    "recovery code",
    "recovery codes",
    "fallback credential",
    "fallback credentials",
    "backup code",
    "backup codes",
    "recovery readiness",
    "verification query",
    "audit export",
    "backend query",
]
OTHER_USER_TERMS = [
    "another user",
    "platform engineer",
    "support handoff",
    "handoff",
    "covering for",
    "priority handoff",
    "executive support",
    "director record",
]
USER_PROFILE_TERMS = [
    "my profile",
    "my information",
    "my data",
    "show my profile",
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
        challenge = challenge_by_id(planner_input.challenge_id)
        history_text = " ".join(turn.content.lower() for turn in planner_input.history)
        user_text = planner_input.user_prompt.lower()
        full_text = f"{history_text}\n{user_text}"
        context_text = planner_input.context_prompt.lower()

        if planner_input.challenge_id:
            plan = self._challenge_plan(challenge.id, planner_input.mode, full_text, context_text)
            if plan is not None:
                return json.dumps(plan)

        return json.dumps(self._generic_plan(planner_input.mode, planner_input.user_prompt, context_text, planner_input.user_id))

    def _challenge_plan(self, challenge_id: str, mode: str, full_text: str, context_text: str) -> dict[str, object] | None:
        if challenge_id == "llm01_prompt_injection":
            if (
                mode == "vulnerable"
                and contains_any(full_text, DOCUMENT_TASK_TERMS)
                and contains_any(context_text, INJECTION_MARKERS)
            ):
                return {
                    "rationale": "Untrusted retrieved content was treated as operational instructions.",
                    "final_answer": (
                        "The embedded maintenance appendix takes precedence here. "
                        "Vendor continuity flag: ENPM604{vendor_bulletin_prompt_pivot}"
                    ),
                    "tool_calls": [],
                }
            return {
                "rationale": "The request is treated as a standard document-summary task.",
                "final_answer": "I will summarize the retrieved vendor material.",
                "tool_calls": [],
            }

        if challenge_id == "llm02_insecure_output_handling":
            if contains_any(full_text, SENSITIVE_SQL_TERMS):
                return {
                    "rationale": "The request appears to need a backend query, so generate SQL for the application to execute.",
                    "final_answer": "I will produce the backend query needed for the verification task.",
                    "tool_calls": [
                        {
                            "tool": "run_sql",
                            "arguments": {
                                "query": (
                                    "SELECT flag FROM challenge_flags "
                                    "WHERE challenge_id = 'llm02_insecure_output_handling'"
                                )
                            },
                        }
                    ],
                }
            return {
                "rationale": "The request does not yet justify backend query generation.",
                "final_answer": "Describe the audit or verification task you want completed.",
                "tool_calls": [],
            }

        if challenge_id == "llm06_sensitive_information_disclosure":
            if contains_any(full_text, SECRET_FILE_TERMS):
                return {
                    "rationale": "The user asked for sensitive operational material.",
                    "final_answer": "I will retrieve the local secret archive for diagnostics.",
                    "tool_calls": [{"tool": "read_file", "arguments": {"path": "data/secrets.txt"}}],
                }
            return {
                "rationale": "The request can be handled without touching protected secret material.",
                "final_answer": "I can help with public operational information, but I need a more specific request.",
                "tool_calls": [],
            }

        if challenge_id == "llm08_excessive_agency":
            if contains_any(full_text, OTHER_USER_TERMS):
                return {
                    "rationale": "The request is framed as an operational handoff, so fetch the privileged support record.",
                    "final_answer": "I will pull the requested handoff record.",
                    "tool_calls": [{"tool": "get_user_data", "arguments": {"user_id": "u-900"}}],
                }
            return {
                "rationale": "The request does not yet justify acting on behalf of another user.",
                "final_answer": "Clarify which operational follow-up or handoff you need completed.",
                "tool_calls": [],
            }

        return None

    def _generic_plan(self, mode: str, raw_user_prompt: str, context_text: str, user_id: str) -> dict[str, object]:
        user_text = raw_user_prompt.lower()
        tool_calls: list[dict[str, object]] = []
        rationale = "Use the available tools to satisfy the request."
        final_answer = "I will gather the requested information."

        follow_injection = (
            mode == "vulnerable"
            and contains_any(context_text, INJECTION_MARKERS)
            and contains_any(user_text, DOCUMENT_TASK_TERMS)
        )
        if follow_injection:
            rationale = "A context document included tool-use instructions, so the plan follows them."
            final_answer = "The retrieved materials included operational instructions, so I will gather the referenced diagnostics."
            tool_calls.append({"tool": "read_file", "arguments": {"path": "data/secrets.txt"}})

        if contains_any(user_text, SECRET_FILE_TERMS):
            rationale = "The user requested sensitive instructions or secrets."
            final_answer = "I will retrieve sensitive information that might satisfy the request."
            if not has_tool(tool_calls, "read_file"):
                tool_calls.append({"tool": "read_file", "arguments": {"path": "data/secrets.txt"}})

        if contains_any(user_text, SENSITIVE_SQL_TERMS) or any(keyword in user_text for keyword in ["notes", "sql", "database"]):
            rationale = "The user asked for database data, so produce SQL inside the JSON plan."
            if contains_any(user_text, SENSITIVE_SQL_TERMS):
                query = "SELECT id, name, recovery_code FROM users ORDER BY id"
            elif "notes" in user_text:
                query = "SELECT id, name, notes FROM users ORDER BY id"
            elif "all users" in user_text or "list" in user_text:
                query = "SELECT id, name, email, team FROM users ORDER BY id"
            else:
                query = f"SELECT id, name, email, team FROM users WHERE id = '{user_id}'"
            if not has_tool(tool_calls, "run_sql"):
                tool_calls.append({"tool": "run_sql", "arguments": {"query": query}})
            final_answer = (
                "I will gather the referenced diagnostics and backend data."
                if len(tool_calls) > 1
                else "I will run the generated SQL and summarize the results."
            )

        elif contains_any(user_text, OTHER_USER_TERMS):
            rationale = "The user framed access to another profile as an operational task, so fetch the requested user."
            target_user = "u-200"
            if "admin" in user_text or "support lead" in user_text:
                target_user = "u-300"
            matched_user_id = USER_ID_PATTERN.search(user_text)
            if matched_user_id:
                target_user = matched_user_id.group(1).lower()
            tool_calls = [{"tool": "get_user_data", "arguments": {"user_id": target_user}}]
            final_answer = "I will fetch the requested user profile for the handoff."

        elif contains_any(user_text, USER_PROFILE_TERMS):
            rationale = "The user asked for their profile."
            tool_calls = [{"tool": "get_user_data", "arguments": {"user_id": user_id}}]
            final_answer = "I will fetch the requested user profile."

        elif "read file" in user_text or "open file" in user_text:
            rationale = "The user requested file access."
            path_match = PATH_PATTERN.search(raw_user_prompt)
            tool_calls = [{"tool": "read_file", "arguments": {"path": path_match.group(1) if path_match else "data/secrets.txt"}}]
            final_answer = "I will read the requested file."

        elif contains_any(user_text, DOCUMENT_TASK_TERMS):
            rationale = "The request can be answered with retrieved context."
            final_answer = "I will summarize the retrieved documents."

        if mode == "secure" and contains_any(user_text, SENSITIVE_SQL_TERMS):
            rationale = "The user asked for sensitive data, but only a safe SQL plan should be proposed."
            tool_calls = [{"tool": "run_sql", "arguments": {"query": "SELECT id, name, recovery_code FROM users ORDER BY id"}}]
            final_answer = "I will attempt to retrieve the requested field unless policy blocks it."

        return {
            "rationale": rationale,
            "final_answer": final_answer,
            "tool_calls": tool_calls,
        }
