from fastapi import APIRouter,Depends, HTTPException, status
from it_career_navigator.schemas import PersonCreate, PersonResponse, PersonLogin, SkillCreate, SkillResponse
from it_career_navigator.auth import oauth2_scheme
from fastapi.security import OAuth2PasswordRequestForm
from it_career_navigator.models import Person, Skills, PersonSkills
from it_career_navigator.database import Get_DB
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from sqlalchemy import select
from it_career_navigator.auth import hash_password, verify_password, CurrentUser
from it_career_navigator.auth import create_access_token
from it_career_navigator.auth import decode_jwt
from it_career_navigator.config import settings


router = APIRouter(tags=["users"], prefix="/users")

@router.get("")
async def read_users():
    return [{"username": "user1"}, {"username": "user2"}]


@router.post("/create_user", response_model=PersonResponse)
async def create_user(
    user: PersonCreate,
    db: Get_DB,
):
    result = await db.execute(
        select(Person).where(Person.email == user.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = Person(
        name=user.name,
        surname=user.surname,
        email=user.email,
        age=user.age,
        phone=user.phone,
        password=hash_password(user.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login")
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Get_DB,
):
    result = await db.execute(
        select(Person).where(Person.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=PersonResponse)
async def read_current_user(
    db: Get_DB,
    current_user: CurrentUser,
):
    user_id = current_user["id"]

    result = await db.execute(
        select(Person).where(Person.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user

@router.get("/{user_id}")
async def read_user(user_id: int):
    return {"username": f"user{user_id}"}


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Get_DB):
    result = await db.execute(
        select(Person).where(Person.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)
    await db.commit()
    return {"detail": "User deleted successfully"}

@router.post('/add_skills')
async def add_skills(
    user_id: int,
    skills: list[SkillCreate],
    current_user: CurrentUser,
    db: Get_DB,
):
    result = await db.execute(
        select(Person).where(Person.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    for skill in skills:
        result = await db.execute(
            select(Skills).where(Skills.name == skill.name)
        )
        db_skill = result.scalar_one_or_none()
        if not db_skill:
            db_skill = Skills(name=skill.name)
            db.add(db_skill)
            await db.commit()
            await db.refresh(db_skill)

        person_skill = PersonSkills(person_id=user.id, skill_id=db_skill.id)
        db.add(person_skill)

    await db.commit()
    await db.refresh(user)
    return user