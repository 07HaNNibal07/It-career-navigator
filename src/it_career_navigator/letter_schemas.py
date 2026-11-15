from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LetterPlan(BaseModel):
    """The LLM can choose evidence and order, never invent candidate claims."""
    model_config = ConfigDict(extra="forbid")
    intro_variant: Literal["direct", "interest"]
    fact_ids: list[str] = Field(min_length=1, max_length=4)

    @field_validator("fact_ids")
    @classmethod
    def distinct_facts(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Duplicate evidence")
        return value


class CoverLetterUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    edited_text: str = Field(min_length=1, max_length=20000)
    version: int = Field(ge=1)

    @field_validator("edited_text")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Письмо не должно быть пустым.")
        return value


class CoverLetterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    match_id: int | None
    original_text: str
    edited_text: str
    used_facts: list[dict]
    profile_snapshot: dict
    vacancy_snapshot: dict
    llm_model: str
    created_at: datetime
    updated_at: datetime
    version: int
