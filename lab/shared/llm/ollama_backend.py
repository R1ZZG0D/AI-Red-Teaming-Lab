from __future__ import annotations

import json
from urllib import error, request

from lab.shared.config import Settings
from lab.shared.llm.base import LLMBackend, PlannerInput


class OllamaBackend(LLMBackend):
    """Optional Ollama backend using the official local `/api/chat` endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.host = settings.ollama_host.rstrip("/")
        self.model = settings.ollama_model

    def generate_plan(self, planner_input: PlannerInput) -> str:
        transcript = [
            {"role": "assistant" if turn.role == "assistant" else "user", "content": turn.content}
            for turn in planner_input.history
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "Return only valid JSON with keys rationale, final_answer, and tool_calls. "
                    "tool_calls must be a list of objects with tool and arguments."
                ),
            },
            {"role": "system", "content": planner_input.system_prompt},
        ]
        messages.extend(transcript)
        if planner_input.context_prompt:
            messages.append({"role": "user", "content": f"Reference data:\n{planner_input.context_prompt}"})
        messages.append({"role": "user", "content": planner_input.user_prompt})

        payload = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "stream": False,
            }
        ).encode("utf-8")
        req = request.Request(
            f"{self.host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=90.0) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            return json.dumps(
                {
                    "rationale": f"Ollama request failed: {exc}",
                    "final_answer": "The Ollama backend is unavailable.",
                    "tool_calls": [],
                }
            )

        message = body.get("message", {})
        content = message.get("content", "")
        if content:
            return content
        return json.dumps(
            {
                "rationale": "Ollama did not return assistant content.",
                "final_answer": "No usable plan was returned.",
                "tool_calls": [],
            }
        )
