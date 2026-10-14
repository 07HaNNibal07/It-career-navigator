from pydantic import BaseModel, EmailStr, Field,ConfigDict


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