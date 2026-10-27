import pytest

from it_career_navigator.services.roadmap import build_roadmap
from it_career_navigator.models import Analysis, Direction, Roadmap, RoadmapItem, Skill, Skill, SkillStatistic, UserSkill,User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from it_career_navigator.tests.conftest import db_session

@pytest.mark.anyio
async def test_build_roadmap(db_session: AsyncSession):
    # Setup test data
    user = User(name="Ilgar", surname="Babaev", email="ilgar@example.com", age=24, phone="+78000554545", password="securepassword")
    python_skill = Skill(name="Python")
    docker_skill = Skill(name="Docker")
    direction = Direction(name="Python Backend")
    db_session.add(user)
    db_session.add(python_skill)
    db_session.add(docker_skill)
    db_session.add(direction)
    await db_session.flush()
    
    user_skill = UserSkill(user_id=user.id, skill_id=python_skill.id)
    db_session.add(user_skill)
    
    analysis = Analysis(user_id=user.id, direction_id=direction.id,status = 'completed')
    db_session.add(analysis)
    
    await db_session.flush()
    
    python_statistic = SkillStatistic(
        analysis_id=analysis.id,
        skill_id=python_skill.id,
        vacancy_count=10,
        demand_percent=100.0,
    )
    docker_statistic = SkillStatistic(
        analysis_id=analysis.id,
        skill_id=docker_skill.id,
        vacancy_count=6,
        demand_percent=60.0,
    )
    db_session.add_all([
        python_statistic,
        docker_statistic,
    ])
    await db_session.flush()
    
    roadmap = await build_roadmap(
        analysis_id=analysis.id,
        current_user_id=user.id,
        db=db_session,
    )

  
    items_result = await db_session.execute(
        select(RoadmapItem).where(
            RoadmapItem.roadmap_id == roadmap.id
        )
    )
    items = items_result.scalars().all()


    assert len(items) == 1
    assert items[0].skill_id == docker_skill.id
    assert items[0].priority == 60.0
    assert python_skill.id not in {
        item.skill_id for item in items
    }