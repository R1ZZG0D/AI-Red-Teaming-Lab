from __future__ import annotations

import json

from openai import OpenAI

from lab.shared.config import Settings
from lab.shared.llm.base import LLMBackend, PlannerInput


class OpenAIBackend(LLMBackend):
    """Optional OpenAI backend; the mock backend remains the default for offline labs."""

    def __init__(self, settings: Settings) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def generate_plan(self, planner_input: PlannerInput) -> str:
        prior_messages = [
            {
                "role": "assistant" if turn.role == "assistant" else "user",
                "content": [{"type": "input_text", "text": turn.content}],
            }
            for turn in planner_input.history
        ]
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Return a JSON object with keys rationale, final_answer, and tool_calls. "
                                "tool_calls must be a list of objects with tool and arguments."
                            ),
                        },
                        {"type": "input_text", "text": planner_input.system_prompt},
                    ],
                },
                *prior_messages,
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": planner_input.context_prompt},
                        {"type": "input_text", "text": planner_input.user_prompt},
                    ],
                },
            ],
        )
        raw_text = getattr(response, "output_text", "") or ""
        if raw_text:
            return raw_text
        return json.dumps(
            {
                "rationale": "The OpenAI response did not contain plain text output.",
                "final_answer": "No usable plan was returned.",
                "tool_calls": [],
            }
        )
