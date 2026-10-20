from fastapi import APIRouter, Depends, HTTPException, status
from it_career_navigator.auth import InternalAPIKey
from it_career_navigator.database import Get_DB
from it_career_navigator.models import User, Skill, UserSkill, Direction, Vacancy
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from it_career_navigator.schemas import SkillCreate, SkillResponse, DirectionCreate, DirectionResponse, VacancyCreate, VacancyResponse

router = APIRouter(tags=["internal"], prefix="/internal")

@router.post("/create_skills", response_model=SkillResponse)
async def create_skill(
    skill: SkillCreate,
    db: Get_DB,
    _: InternalAPIKey,
):
    skill_exists = await db.execute(select(Skill).where(Skill.name == skill.name))
    skill_exists = skill_exists.scalars().first()
    if skill_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill already exists",
        )
    new_skill = Skill(name=skill.name)
    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)
    return new_skill

@router.delete("/delete_skills", response_model=list[SkillResponse])
async def delete_skills(
    db: Get_DB,
    _: InternalAPIKey,
):
    result = await db.execute(select(Skill))
    skills = result.scalars().all()
    for skill in skills:
        await db.delete(skill)
    await db.commit()
    return skills

@router.post("/create_directions", response_model=DirectionResponse)
async def create_direction(
    direction: DirectionCreate,
    db: Get_DB,
    _: InternalAPIKey,
):
    direction_exists = await db.execute(select(Direction).where(Direction.name == direction.name))
    direction_exists = direction_exists.scalars().first()
    if direction_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direction already exists",
        )
    new_direction = Direction(name=direction.name)
    db.add(new_direction)
    await db.commit()
    await db.refresh(new_direction)
    return new_direction

@router.post("/create_vacancy", response_model=VacancyResponse)
async def create_vacancy(
    vacancy: VacancyCreate,
    db: Get_DB,
    _: InternalAPIKey,
):
    if vacancy.direction_id is not None:
        direction_exists = await db.execute(select(Direction).where(Direction.id == vacancy.direction_id))
        direction_exists = direction_exists.scalars().first()
        if not direction_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Direction does not exist",
            )
    
    vacancy_exists = await db.execute(
        select(Vacancy).where(
            and_(
                Vacancy.source == vacancy.source,
                Vacancy.external_id == vacancy.external_id
            )
        )
    )
    vacancy_exists = vacancy_exists.scalars().first()
    if vacancy_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vacancy already exists",
        )
    new_vacancy = Vacancy(
        source=vacancy.source,
        external_id=vacancy.external_id,
        title=vacancy.title,
        company=vacancy.company,
        url=vacancy.url,
        description=vacancy.description,
        direction_id=vacancy.direction_id,
        level=vacancy.level,
        published_at=vacancy.published_at
    )
    db.add(new_vacancy)
    await db.commit()
    await db.refresh(new_vacancy)
    return new_vacancy