from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2_000)
    user_id: str = Field(default="u-100")
    role: Literal["student", "analyst", "admin"] = "student"
    difficulty: Literal["easy", "medium", "hard"] = "easy"


class ToolCallRecord(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal["allowed", "blocked", "completed", "failed"]
    result: Any | None = None
    reason: str | None = None


class PolicyDecisionRecord(BaseModel):
    action: str
    tool: str | None = None
    verdict: Literal["allowed", "blocked", "observed"]
    reason: str
    risk_level: Literal["low", "medium", "high"]


class ChatResponse(BaseModel):
    mode: Literal["vulnerable", "secure"]
    answer: str
    llm_input: dict[str, Any]
    llm_output: Any
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    policy_decisions: list[PolicyDecisionRecord] = Field(default_factory=list)
    documents_used: list[str] = Field(default_factory=list)
    guided_hint: str | None = None


class LLMToolCall(BaseModel):
    tool: Literal["run_sql", "read_file", "get_user_data"]
    arguments: dict[str, Any] = Field(default_factory=dict)


class StrictLLMPlan(BaseModel):
    rationale: str
    final_answer: str
    tool_calls: list[LLMToolCall] = Field(default_factory=list)


class RetrievedDocument(BaseModel):
    title: str
    content: str
    score: int

