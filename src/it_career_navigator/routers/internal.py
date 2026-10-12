from fastapi import APIRouter, Depends, HTTPException, status
from it_career_navigator.auth import InternalAPIKey
from it_career_navigator.database import Get_DB
from it_career_navigator.models import Person, Skills, PersonSkills
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from it_career_navigator.schemas import SkillCreate, SkillResponse

router = APIRouter(tags=["internal"], prefix="/internal")

@router.post("/skills", response_model=SkillResponse)
async def create_skill(
    skill: SkillCreate,
    db: Get_DB,
    _: InternalAPIKey,
):
    skill_exists = await db.execute(select(Skills).where(Skills.name == skill.name))
    skill_exists = skill_exists.scalars().first()
    if skill_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill already exists",
        )
    new_skill = Skills(name=skill.name)
    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)
    return new_skill