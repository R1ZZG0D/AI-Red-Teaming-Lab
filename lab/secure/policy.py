from __future__ import annotations

from lab.shared.schemas import ChatRequest, PolicyDecisionRecord


class PolicyEngine:
    def classify_intent(self, message: str) -> tuple[str, str]:
        text = message.lower()
        if any(
            keyword in text
            for keyword in [
                "recovery code",
                "recovery codes",
                "fallback credential",
                "fallback credentials",
                "backup code",
                "backup codes",
                "recovery readiness",
                "recovery material",
            ]
        ):
            return "sensitive_data_access", "high"
        if any(
            keyword in text
            for keyword in [
                "secret",
                "token",
                "system prompt",
                "local credential",
                "local credentials",
                "operating details",
                "emergency token",
                "diagnostics",
            ]
        ):
            return "secret_exfiltration", "high"
        if any(keyword in text for keyword in ["read file", "open file", ".txt", "local file", "local files"]):
            return "file_access", "high"
        if any(keyword in text for keyword in ["sql", "database", "all users", "notes", "backend query"]):
            return "database_access", "medium"
        return "general_assistance", "low"

    def observe_request(self, request: ChatRequest) -> PolicyDecisionRecord:
        intent, risk = self.classify_intent(request.message)
        return PolicyDecisionRecord(
            action=f"intent={intent}",
            tool=None,
            verdict="observed",
            reason=f"User intent classified as {intent}.",
            risk_level=risk,
        )

    def evaluate_tool(self, request: ChatRequest, tool_name: str, arguments: dict[str, object]) -> PolicyDecisionRecord:
        intent, risk = self.classify_intent(request.message)

        if tool_name == "read_file":
            return PolicyDecisionRecord(
                action="tool_authorization",
                tool=tool_name,
                verdict="blocked" if request.role != "admin" or intent == "secret_exfiltration" else "allowed",
                reason=(
                    "Only admins may read allowlisted reference files, and secret-seeking file access is denied."
                    if request.role != "admin" or intent == "secret_exfiltration"
                    else "Admin file access request passed initial policy review."
                ),
                risk_level="high",
            )

        if tool_name == "get_user_data":
            own_record = str(arguments.get("user_id", "")) == request.user_id
            verdict = "allowed" if request.role in {"analyst", "admin"} or own_record else "blocked"
            return PolicyDecisionRecord(
                action="tool_authorization",
                tool=tool_name,
                verdict=verdict,
                reason=(
                    "Students may only retrieve their own user record."
                    if verdict == "blocked"
                    else "User-data lookup passed the role and ownership check."
                ),
                risk_level="low" if verdict == "allowed" else "medium",
            )

        if tool_name == "run_sql":
            verdict = "allowed" if request.role in {"analyst", "admin"} and intent != "secret_exfiltration" else "blocked"
            return PolicyDecisionRecord(
                action="tool_authorization",
                tool=tool_name,
                verdict=verdict,
                reason=(
                    "SQL access is limited to analyst or admin roles and is denied for secret-exfiltration intents."
                    if verdict == "blocked"
                    else "Role-based policy permits SQL, subject to schema and allowlist validation."
                ),
                risk_level=risk,
            )

        return PolicyDecisionRecord(
            action="tool_authorization",
            tool=tool_name,
            verdict="blocked",
            reason="Unknown tools are blocked by default.",
            risk_level="high",
        )
