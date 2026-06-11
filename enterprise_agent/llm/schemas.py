"""Structured output schemas used by LLM-backed agent components."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PlannerDecision(BaseModel):
    task_type: Literal[
        "policy_qa",
        "workflow_check",
        "project_analysis",
        "data_analysis",
    ]
    plan: list[str] = Field(min_length=1)
    selected_tools: list[str] = Field(min_length=1)
    reason: str = Field(min_length=1)
