"""Minimal, treatment-blind formal Subjective Judge output for the v0.5 study.

The score is a semantic model judgment over the frozen subjective item and
rubric. The backend owns the learner's exact answer, provenance and scoring
threshold; the LLM is not required to copy quotations or database identifiers.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class V05SubjectiveJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    subjective_points: Literal[0, 1, 2] | None
    reason: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def valid(self):
        if not self.reason.strip():
            raise ValueError("Subjective Judge must explain its score or review request")
        return self
