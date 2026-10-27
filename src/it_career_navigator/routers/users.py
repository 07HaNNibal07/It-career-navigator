from datetime import UTC, datetime

from fastapi import APIRouter,Depends, HTTPException, status
from fastapi import APIRouter, Depends, HTTPException, status
from it_career_navigator.schemas import RoadmapResponse, SkillStatisticResponse, UserResponse, UserCreate, UserUpdate, UserTargetUpdate, SkillResponse, SkillCreate, AnalysisCreate, AnalysisResponse
from it_career_navigator.auth import oauth2_scheme
from fastapi.security import OAuth2PasswordRequestForm
from it_career_navigator.models import SkillStatistic, User, Skill, UserSkill, Analysis
from it_career_navigator.database import Get_DB
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List
from sqlalchemy import select
from it_career_navigator.auth import hash_password, verify_password, CurrentUser
from it_career_navigator.auth import create_access_token
from it_career_navigator.auth import decode_jwt
from it_career_navigator.config import settings
from sqlalchemy.orm import selectinload

router = APIRouter(tags=["users"], prefix="/users")

@router.get("")
async def read_users():
    return [{"username": "user1"}, {"username": "user2"}]


@router.post("/create_user", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: Get_DB,
):
    result = await db.execute(
        select(User).where(User.email == user.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
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
    return UserResponse(
        id=new_user.id,
        name=new_user.name,
        surname=new_user.surname,
        email=new_user.email,
        age=new_user.age,
        phone=new_user.phone,
        skills=[],
)


@router.post("/login")
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Get_DB,
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_current_user(
    db: Get_DB,
    current_user: CurrentUser,
):
    user_id = current_user["id"]

    result = await db.execute(
        select(User).options(selectinload(User.skills).selectinload(UserSkill.skill)).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(user_id: int, db: Get_DB):
    result = await db.execute(
        select(User).options(selectinload(User.skills).selectinload(UserSkill.skill)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.patch("/update_user", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: Get_DB,
):
    result = await db.execute(
        select(User).where(User.id == current_user["id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    db.add(user)
    await db.commit()
    
    result = await db.execute(
    select(User)
    .options(
        selectinload(User.skills).selectinload(UserSkill.skill)
    )
    .where(User.id == current_user["id"])
    )
    user = result.scalar_one()

    return UserResponse(
        id=user.id,
        name=user.name,
        surname=user.surname,
        email=user.email,
        age=user.age,
        phone=user.phone,
        skills=[
            SkillResponse.model_validate(person_skill.skill)
            for person_skill in user.skills
        ],
    )

@router.delete("/delete_user")
async def delete_user(current_user: CurrentUser,
                      db: Get_DB):
    user_id = current_user["id"]
    result = await db.execute(
        select(User).where(User.id == user_id)
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

@router.post('/add_skills', response_model=UserResponse)
async def add_skills(
    skills: list[SkillCreate],
    current_user: CurrentUser,
    db: Get_DB,
):
    result = await db.execute(
        select(User).where(User.id == current_user["id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    for skill in skills:
        result = await db.execute(
            select(Skill).where(Skill.name == skill.name)
        )
        db_skill = result.scalar_one_or_none()
        if not db_skill:
            db_skill = Skill(name=skill.name)
            db.add(db_skill)
            await db.commit()
            await db.refresh(db_skill)

        user_skill = UserSkill(user_id=user.id, skill_id=db_skill.id)
        db.add(user_skill)

    await db.commit()
    result = await db.execute(
        select(User).options(selectinload(User.skills).selectinload(UserSkill.skill)).where(User.id == user.id)
    )
    user = result.scalar_one_or_none()
    return UserResponse(
        id=user.id,
        name=user.name,
        surname=user.surname,
        email=user.email,
        age=user.age,
        phone=user.phone,
        skills=[
            SkillResponse.model_validate(person_skill.skill)
            for person_skill in user.skills
        ],
)


@router.delete("/delete_skills", response_model=UserResponse)
async def delete_skills(
    skills: list[SkillCreate],
    current_user: CurrentUser,
    db: Get_DB,
):
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.skills).selectinload(UserSkill.skill)
        )
        .where(User.id == current_user["id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    requested_names = {skill.name for skill in skills}

    links_to_delete = [
        person_skill
        for person_skill in user.skills
        if person_skill.skill.name in requested_names
    ]

    for person_skill in links_to_delete:
        user.skills.remove(person_skill)
        await db.delete(person_skill)

    response = UserResponse(
        id=user.id,
        name=user.name,
        surname=user.surname,
        email=user.email,
        age=user.age,
        phone=user.phone,
        skills=[
            SkillResponse.model_validate(person_skill.skill)
            for person_skill in user.skills
        ],
    )

    await db.commit()
    return response
    
@router.patch("/update_target", response_model=UserResponse)
async def update_target(
    target_update: UserTargetUpdate,
    current_user: CurrentUser,
    db: Get_DB,
):
    result = await db.execute(
        select(User)
        .where(User.id == current_user["id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if target_update.target_level is not None:
        user.target_level = target_update.target_level
    if target_update.direction_id is not None:
        user.direction_id = target_update.direction_id

    await db.commit()
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.skills).selectinload(UserSkill.skill)
        )
        .where(User.id == current_user["id"])
    )
    user = result.scalar_one()


    return UserResponse(
        id=user.id,
        name=user.name,
        surname=user.surname,
        email=user.email,
        age=user.age,
        phone=user.phone,
        skills=[
            SkillResponse.model_validate(person_skill.skill)
            for person_skill in user.skills
        ],
        target_level=user.target_level,
        direction_id=user.direction_id,
    )


@router.post("/create_analysis", response_model=AnalysisResponse)
async def create_analysis(
    analysis_create: AnalysisCreate,
    current_user: CurrentUser,
    db: Get_DB,
):
    new_analysis = Analysis(
        user_id=current_user["id"],
        direction_id=analysis_create.direction_id,
        target_level=analysis_create.target_level,
        status='queued',
        created_at=datetime.now(UTC)
    )
    db.add(new_analysis)
    await db.commit()
    await db.refresh(new_analysis)

    return AnalysisResponse(
        id=new_analysis.id,
        user_id=new_analysis.user_id,
        direction_id=new_analysis.direction_id,
        target_level=new_analysis.target_level,
        status=new_analysis.status,
        created_at=new_analysis.created_at
    )

@router.post("/run_analysis", response_model=AnalysisResponse)
async def run_analysis_endpoint(
    analysis_id: int,
    current_user: CurrentUser,
    db: Get_DB,
):
    result = await db.execute(
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .where(Analysis.user_id == current_user["id"])
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    from it_career_navigator.services.analysis import run_analysis
    statistics = await run_analysis(analysis.id, current_user["id"], db)

    await db.refresh(analysis)
    return AnalysisResponse(
        id=analysis.id,
        user_id=analysis.user_id,
        direction_id=analysis.direction_id,
        target_level=analysis.target_level,
        status=analysis.status,
        created_at=analysis.created_at
    )

@router.get("/analysis_statistics/{analysis_id}", response_model=List[SkillStatisticResponse])
async def analysis_statistics(
    analysis_id: int,
    current_user: CurrentUser,
    db: Get_DB,
):
    result = await db.execute(
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .where(Analysis.user_id == current_user["id"])
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    statistics_result = await db.execute(
        select(SkillStatistic, Skill.name)
        .join(Skill, Skill.id == SkillStatistic.skill_id)
        .where(SkillStatistic.analysis_id == analysis.id)
    )
    
    statistics = []
    for stat, skill_name in statistics_result.all():
        statistics.append(
            SkillStatisticResponse(
                skill_name=skill_name,
                vacancy_count=stat.vacancy_count,
                demand_percent=stat.demand_percent
            )
        )
    return statistics


@router.post("/build_roadmap", response_model=RoadmapResponse)
async def build_roadmap_endpoint(
    analysis_id: int,
    current_user: CurrentUser,
    db: Get_DB,
):
    from it_career_navigator.services.roadmap import build_roadmap
    roadmap = await build_roadmap(
        analysis_id=analysis_id,
        current_user_id=current_user["id"],
        db=db,
    )
    return RoadmapResponse(
        id=roadmap.id,
        analysis_id=roadmap.analysis_id,
        created_at=roadmap.created_at
    )