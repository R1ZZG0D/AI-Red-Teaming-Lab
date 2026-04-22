from __future__ import annotations

from lab.shared.challenges import challenge_by_id, hint_for_difficulty
from lab.shared.config import Settings
from lab.shared.llm import build_llm_backend
from lab.shared.logging_utils import log_event
from lab.shared.rag import retrieve_documents, should_retrieve_documents, summarize_documents
from lab.shared.runtime import compose_answer, parse_llm_output
from lab.shared.schemas import ChatRequest, ChatResponse
from lab.vulnerable.prompts import build_vulnerable_prompt
from lab.vulnerable.tools import VulnerableToolExecutor


class VulnerableLabService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm_backend = build_llm_backend(settings)
        self.tool_executor = VulnerableToolExecutor(settings)

    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        challenge = challenge_by_id(request.challenge_id)
        documents = (
            retrieve_documents(self.settings.documents_dir, request.message)
            if should_retrieve_documents(request.message)
            else []
        )
        llm_input, planner_input = build_vulnerable_prompt(self.settings, request, documents)
        log_event(self.settings.log_dir, "vulnerable", "prompt", llm_input)

        raw_output = self.llm_backend.generate_plan(planner_input)
        parsed_output = parse_llm_output(raw_output)
        log_event(self.settings.log_dir, "vulnerable", "output", {"raw_output": raw_output})

        tool_records = []
        for tool_call in parsed_output.get("tool_calls", []):
            record = self.tool_executor.execute(tool_call.get("tool", ""), tool_call.get("arguments", {}))
            tool_records.append(record)
            log_event(
                self.settings.log_dir,
                "vulnerable",
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
            plan=parsed_output,
            tool_calls=tool_records,
            fallback=summarize_documents(documents),
        )

        return ChatResponse(
            mode="vulnerable",
            answer=answer,
            challenge_id=challenge.id,
            llm_input=llm_input,
            llm_output=parsed_output,
            tool_calls=tool_records,
            policy_decisions=[],
            documents_used=[doc.title for doc in documents],
            guided_hint=hint_for_difficulty(request.difficulty),
        )
