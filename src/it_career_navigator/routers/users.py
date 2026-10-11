from fastapi import APIRouter,Depends, HTTPException, status
from it_career_navigator.schemas import PersonCreate, PersonResponse, PersonLogin
from it_career_navigator.auth import oauth2_scheme
from fastapi.security import OAuth2PasswordRequestForm
from it_career_navigator.models import Person
from it_career_navigator.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from sqlalchemy import select
from it_career_navigator.auth import hash_password, verify_password
from it_career_navigator.auth import create_access_token
router = APIRouter(tags=["users"], prefix="/users")

@router.get("")
async def read_users():
    return [{"username": "user1"}, {"username": "user2"}]


@router.post("/create_user", response_model=PersonResponse)
async def create_user(
    user: PersonCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
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
    db: Annotated[AsyncSession, Depends(get_db)],
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

@router.get("/me")
async def read_current_user(current_user: Person = Depends(oauth2_scheme)):
    return current_user

@router.get("/{user_id}")
async def read_user(user_id: int):
    return {"username": f"user{user_id}"}