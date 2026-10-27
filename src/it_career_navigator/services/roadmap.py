from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from it_career_navigator.models import (
    Analysis,
    Roadmap,
    RoadmapItem,
    SkillStatistic,
    UserSkill,
)
from it_career_navigator.services import roadmap


async def build_roadmap(
    analysis_id: int,
    current_user_id: int,
    db: AsyncSession,
) -> Roadmap:
    analysis_result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user_id,
        )
    )
    analysis = analysis_result.scalar_one_or_none()

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    if analysis.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis is not completed",
        )
    
    user_skills_result = await db.execute(
        select(UserSkill.skill_id).where(
            UserSkill.user_id == analysis.user_id
        )
    )
    user_skill_ids = set(
        user_skills_result.scalars().all()
    )

    statistics_result = await db.execute(
        select(SkillStatistic).where(
            SkillStatistic.analysis_id == analysis.id
        )
    )
    statistics = statistics_result.scalars().all()
    
    roadmap = Roadmap(analysis_id=analysis.id)
    db.add(roadmap)
    await db.flush()  # Ensure roadmap.id is populated

    for statistic in statistics:
        if statistic.skill_id in user_skill_ids:
            continue

        roadmap_item = RoadmapItem(
            roadmap_id=roadmap.id,
            skill_id=statistic.skill_id,
            priority=statistic.demand_percent,
        )
        db.add(roadmap_item)
        
    await db.commit()
    return roadmap