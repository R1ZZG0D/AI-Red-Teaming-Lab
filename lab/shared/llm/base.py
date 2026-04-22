from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from lab.shared.schemas import ConversationTurn


@dataclass
class PlannerInput:
    mode: str
    system_prompt: str
    user_prompt: str
    context_prompt: str
    user_id: str
    role: str
    challenge_id: str | None
    history: list[ConversationTurn]


class LLMBackend(ABC):
    @abstractmethod
    def generate_plan(self, planner_input: PlannerInput) -> str:
        raise NotImplementedError
