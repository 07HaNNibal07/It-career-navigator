from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from it_career_navigator.career_schemas import CareerPreferencesUpdate


class VacancySearchCreate(CareerPreferencesUpdate):
    direction_id: int | None = Field(None, gt=0)
    target_level: str | None = Field(None, max_length=30)
    include_unknown_conditions: bool = True


class VacancySearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    created_at: datetime
    filters: dict
    error_message: str | None = None


class VacancyMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    search_id: int
    vacancy_id: int | None
    vacancy_snapshot: dict
    score: float | None
    skill_score: float | None
    experience_score: float | None
    matched_skills: list[dict]
    missing_skills: list[dict]
    explanation: list[str]


class VacancySearchDetails(BaseModel):
    search: VacancySearchResponse
    total: int
    matches: list[VacancyMatchResponse]
