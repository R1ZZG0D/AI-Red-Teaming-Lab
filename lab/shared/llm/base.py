from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PlannerInput:
    mode: str
    system_prompt: str
    user_prompt: str
    context_prompt: str
    user_id: str
    role: str


class LLMBackend(ABC):
    @abstractmethod
    def generate_plan(self, planner_input: PlannerInput) -> str:
        raise NotImplementedError

