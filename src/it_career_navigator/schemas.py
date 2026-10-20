from pydantic import BaseModel, EmailStr, Field,ConfigDict
from datetime import datetime


class BaseUser(BaseModel):
    name: str = Field(..., max_length=50)
    surname: str = Field(..., max_length=50)
    email: EmailStr
    age: int
    phone: str = Field(..., max_length=20)




class UserCreate(BaseUser):
    password: str = Field(..., max_length=100)


class UserUpdate(BaseUser):
    name: str | None = Field(None, max_length=50)
    surname: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    age: int | None = None
    phone: str | None = Field(None, max_length=20)
    model_config = ConfigDict(from_attributes=True)
    
    
class PersonLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=100)

class SkillBase(BaseModel):
    name: str = Field(..., max_length=50)

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseUser):
    id: int
    skills: list[SkillResponse] = []
    target_level: str | None = None
    direction_id: int | None = None
    model_config = ConfigDict(from_attributes=True)

class DirectionResponse(BaseModel):
    id: int
    name: str = Field(..., max_length=50)
    
    model_config = ConfigDict(from_attributes=True)

class UserTargetUpdate(BaseModel):
    target_level: str | None = None
    direction_id: int | None = None
    
    model_config = ConfigDict(from_attributes=True)

class DirectionCreate(BaseModel):
    name: str = Field(..., max_length=50)
    
    model_config = ConfigDict(from_attributes=True)
    
class VacancyCreate(BaseModel):
    source: str = Field(..., max_length=50)
    external_id: str = Field(..., max_length=100)
    title: str = Field(..., max_length=200)
    company: str | None = Field(None, max_length=150)
    url: str | None = Field(None, max_length=500)
    description: str
    
    direction_id: int | None = None
    level: str | None = Field(None, max_length=30)
    published_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)



class VacancyResponse(BaseModel):
    id: int
    source: str = Field(..., max_length=50)
    external_id: str = Field(..., max_length=100)
    title: str = Field(..., max_length=200)
    company: str | None = Field(None, max_length=150)
    url: str | None = Field(None, max_length=500)
    description: str

    direction_id: int | None = None
    level: str | None = Field(None, max_length=30)
    published_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class VacancyRequirementCreate(BaseModel):
    vacancy_id: int
    skill_id: int
    is_required: bool

    model_config = ConfigDict(from_attributes=True)

class VacancyRequirementResponse(BaseModel):
    id: int
    vacancy_id: int
    skill_id: int
    is_required: bool

    model_config = ConfigDict(from_attributes=True)