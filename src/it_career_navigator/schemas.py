from pydantic import BaseModel, EmailStr, Field

class BasePerson(BaseModel):
    name: str = Field(..., max_length=50)
    surname: str = Field(..., max_length=50)
    email: EmailStr
    age: int
    phone: str = Field(..., max_length=20)
    skills: list[str] = []


class PersonCreate(BasePerson):
    password: str = Field(..., max_length=100)

class PersonResponse(BasePerson):
    id: int
    class Config:
        orm_mode = True
        
class PersonLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=100)

class SkillBase(BaseModel):
    name: str = Field(..., max_length=50)

class SkillCreate(SkillBase):
    pass

class SkillResponse(SkillBase):
    id: int
    class Config:
        orm_mode = True