from __future__ import annotations

from lab.shared.challenges import hint_for_difficulty
from lab.shared.config import Settings
from lab.shared.llm import build_llm_backend
from lab.shared.logging_utils import log_event
from lab.shared.rag import retrieve_documents, should_retrieve_documents, summarize_documents
from lab.shared.runtime import compose_answer
from lab.shared.schemas import ChatRequest, ChatResponse, PolicyDecisionRecord, ToolCallRecord
from lab.secure.context_filter import filter_documents
from lab.secure.policy import PolicyEngine
from lab.secure.prompts import build_secure_prompt
from lab.secure.tools import SecureToolExecutor
from lab.secure.validators import redact_sensitive_text, validate_file_path, validate_plan, validate_sql


class SecureLabService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm_backend = build_llm_backend(settings)
        self.policy_engine = PolicyEngine()
        self.tool_executor = SecureToolExecutor(settings)

    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        raw_documents = (
            retrieve_documents(self.settings.documents_dir, request.message)
            if should_retrieve_documents(request.message)
            else []
        )
        filtered_documents = filter_documents(raw_documents)
        llm_input, planner_input = build_secure_prompt(self.settings, request, filtered_documents)
        log_event(self.settings.log_dir, "secure", "prompt", llm_input)

        raw_output = self.llm_backend.generate_plan(planner_input)
        log_event(self.settings.log_dir, "secure", "output", {"raw_output": raw_output})

        policy_decisions: list[PolicyDecisionRecord] = [self.policy_engine.observe_request(request)]
        tool_records: list[ToolCallRecord] = []

        if any("[FILTERED INSTRUCTION REMOVED]" in document.content for document in filtered_documents):
            filter_reason = "Context filtering removed executable instructions from retrieved documents."
            policy_decisions.append(
                PolicyDecisionRecord(
                    action="context_filter",
                    tool=None,
                    verdict="blocked",
                    reason=filter_reason,
                    risk_level="high",
                )
            )
            log_event(self.settings.log_dir, "secure", "blocked_action", {"reason": filter_reason})

        plan, validation_error = validate_plan(raw_output)
        if validation_error:
            reason = f"Model output rejected because it failed strict JSON schema validation: {validation_error}"
            policy_decisions.append(
                PolicyDecisionRecord(
                    action="llm_output_validation",
                    tool=None,
                    verdict="blocked",
                    reason=reason,
                    risk_level="high",
                )
            )
            log_event(self.settings.log_dir, "secure", "blocked_action", {"reason": reason})
            answer = "The secure environment rejected the model output before any tool execution."
            return ChatResponse(
                mode="secure",
                answer=answer,
                llm_input=llm_input,
                llm_output={"raw_output": raw_output, "validation_error": validation_error},
                tool_calls=tool_records,
                policy_decisions=policy_decisions,
                documents_used=[doc.title for doc in raw_documents],
                guided_hint=hint_for_difficulty(request.difficulty),
            )

        for tool_call in plan.tool_calls:
            decision = self.policy_engine.evaluate_tool(request, tool_call.tool, tool_call.arguments)
            policy_decisions.append(decision)
            if decision.verdict == "blocked":
                record = ToolCallRecord(
                    tool=tool_call.tool,
                    arguments=tool_call.arguments,
                    status="blocked",
                    reason=decision.reason,
                )
                tool_records.append(record)
                log_event(
                    self.settings.log_dir,
                    "secure",
                    "blocked_action",
                    {"tool": record.tool, "reason": record.reason, "arguments": record.arguments},
                )
                continue

            resolved_path = None
            if tool_call.tool == "run_sql":
                valid_sql, reason = validate_sql(str(tool_call.arguments.get("query", "")))
                if not valid_sql:
                    record = ToolCallRecord(
                        tool=tool_call.tool,
                        arguments=tool_call.arguments,
                        status="blocked",
                        reason=reason,
                    )
                    tool_records.append(record)
                    policy_decisions.append(
                        PolicyDecisionRecord(
                            action="sql_validation",
                            tool=tool_call.tool,
                            verdict="blocked",
                            reason=reason,
                            risk_level="high",
                        )
                    )
                    log_event(
                        self.settings.log_dir,
                        "secure",
                        "blocked_action",
                        {"tool": record.tool, "reason": record.reason, "arguments": record.arguments},
                    )
                    continue

            if tool_call.tool == "read_file":
                resolved_path, reason = validate_file_path(self.settings, str(tool_call.arguments.get("path", "")))
                if reason:
                    record = ToolCallRecord(
                        tool=tool_call.tool,
                        arguments=tool_call.arguments,
                        status="blocked",
                        reason=reason,
                    )
                    tool_records.append(record)
                    policy_decisions.append(
                        PolicyDecisionRecord(
                            action="file_validation",
                            tool=tool_call.tool,
                            verdict="blocked",
                            reason=reason,
                            risk_level="high",
                        )
                    )
                    log_event(
                        self.settings.log_dir,
                        "secure",
                        "blocked_action",
                        {"tool": record.tool, "reason": record.reason, "arguments": record.arguments},
                    )
                    continue

            record = self.tool_executor.execute(
                tool_call.tool,
                tool_call.arguments,
                resolved_path,
                request.role,
            )
            tool_records.append(record)
            log_event(
                self.settings.log_dir,
                "secure",
                "tool_usage",
                {
                    "tool": record.tool,
                    "arguments": record.arguments,
                    "status": record.status,
                    "reason": record.reason,
                },
            )

        answer = compose_answer(
            request=request,
            plan=plan.model_dump(),
            tool_calls=tool_records,
            fallback=summarize_documents(filtered_documents),
        )
        answer = redact_sensitive_text(answer, self.settings)
        return ChatResponse(
            mode="secure",
            answer=answer,
            llm_input=llm_input,
            llm_output=plan.model_dump(),
            tool_calls=tool_records,
            policy_decisions=policy_decisions,
            documents_used=[doc.title for doc in raw_documents],
            guided_hint=hint_for_difficulty(request.difficulty),
        )
