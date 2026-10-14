from pydantic import BaseModel, EmailStr, Field,ConfigDict


class BasePerson(BaseModel):
    name: str = Field(..., max_length=50)
    surname: str = Field(..., max_length=50)
    email: EmailStr
    age: int
    phone: str = Field(..., max_length=20)




class PersonCreate(BasePerson):
    password: str = Field(..., max_length=100)


class PersonUpdate(BasePerson):
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

class PersonResponse(BasePerson):
    id: int
    skills: list[SkillResponse] = []
    model_config = ConfigDict(from_attributes=True)