from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, field_validator, model_validator


WORK_FORMATS = {"remote": "Удалённо", "office": "Офис", "hybrid": "Гибрид"}
EMPLOYMENT_TYPES = {"full_time": "Полная занятость", "part_time": "Частичная занятость", "internship": "Стажировка", "contract": "Проектная работа"}
WorkFormat = Literal["remote", "office", "hybrid"]
EmploymentType = Literal["full_time", "part_time", "internship", "contract"]
SkillName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class CareerPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    desired_position: str | None = Field(None, max_length=200)
    city: str | None = Field(None, max_length=100)
    work_formats: list[WorkFormat] = Field(default_factory=list)
    employment_types: list[EmploymentType] = Field(default_factory=list)

    @field_validator("desired_position", "city")
    @classmethod
    def blank_to_none(cls, value):
        return value or None

    @field_validator("work_formats", "employment_types")
    @classmethod
    def unique_values(cls, value):
        return list(dict.fromkeys(value))


class ExperienceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    position: str = Field(min_length=1, max_length=200)
    organization: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date | None = None
    description: str = Field("", max_length=10000)
    achievements: str = Field("", max_length=10000)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.start_date > date.today() or (self.end_date and self.end_date > date.today()):
            raise ValueError("Даты опыта не могут быть в будущем.")
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("Дата окончания должна быть не раньше даты начала.")
        return self


class ExperienceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    position: str | None = None
    organization: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    achievements: str | None = None


class ExperienceResponse(ExperienceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field("", max_length=10000)
    role: str = Field(min_length=1, max_length=200)
    url: HttpUrl | None = Field(None, max_length=500)
    skill_ids: list[int] = Field(default_factory=list, max_length=100)
    skill_names: list[SkillName] = Field(default_factory=list, max_length=100)

    @field_validator("skill_ids")
    @classmethod
    def unique_skills(cls, value):
        if any(item <= 0 for item in value):
            raise ValueError("ID навыка должен быть положительным.")
        return list(dict.fromkeys(value))


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    description: str | None = None
    role: str | None = None
    url: HttpUrl | None = None
    skill_ids: list[int] | None = Field(None, max_length=100)
    skill_names: list[SkillName] = Field(default_factory=list, max_length=100)


class ProjectResponse(ProjectCreate):
    id: int


class CareerProfileResponse(CareerPreferencesUpdate):
    experiences: list[ExperienceResponse]
    projects: list[ProjectResponse]
