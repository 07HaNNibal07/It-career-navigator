import pytest

from it_career_navigator.services.analysis import run_analysis
from it_career_navigator.models import (
    Analysis,
    SkillStatistic,
    Vacancy,
    VacancyRequirement,
    User,
    Direction,
    Skill,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from it_career_navigator.tests.conftest import db_session




@pytest.mark.anyio
async def test_run_analysis(db_session: AsyncSession):
    direction = Direction(name="Python Backend")
    user = User(name="Ilgar", surname="Babaev", email="ilgar@example.com", age=24, phone="+78000554545", password="securepassword")
    python_skill = Skill(name="Python")
    docker_skill = Skill(name="Docker")
    
    db_session.add_all([direction, user, python_skill, docker_skill])
    await db_session.flush()
    
    analysis = Analysis(user_id=user.id, direction_id=direction.id)
    
    first_vacancy = Vacancy(
        source="test",
        external_id="analysis-001",
        title="Junior Python Developer",
        description="Python and Docker",
        direction_id=direction.id,
        level="Junior"
    )
    
    second_vacancy = Vacancy(
        source="test",
        external_id="analysis-002",
        title="Junior Python Developer",
        description="Python and Docker",
        direction_id=direction.id,
        level="Junior"
    )
  
    db_session.add_all([analysis, first_vacancy, second_vacancy])
    await db_session.flush()
    
    vr1 = VacancyRequirement(vacancy_id=first_vacancy.id, skill_id=python_skill.id)
    vr2 = VacancyRequirement(vacancy_id=second_vacancy.id, skill_id=python_skill.id)
    vr3 = VacancyRequirement(vacancy_id=second_vacancy.id, skill_id=docker_skill.id)
    db_session.add_all([vr1, vr2, vr3])
    await db_session.flush()
    
    statistics = await run_analysis(analysis.id,user.id, db_session)
    
    await db_session.refresh(analysis)
    assert analysis.status == "completed"
    
    assert len(statistics) ==2
    
    python_statistic = next(stat for stat in statistics if stat.skill_id == python_skill.id)
    assert python_statistic.vacancy_count == 2

    docker_statistic = next(stat for stat in statistics if stat.skill_id == docker_skill.id)
    assert docker_statistic.vacancy_count == 1
    
    demand_percent = python_statistic.vacancy_count / len([first_vacancy, second_vacancy]) * 100
    assert demand_percent == 100.0

    docker_demand_percent = docker_statistic.vacancy_count / len([first_vacancy, second_vacancy]) * 100
    assert docker_demand_percent == 50.0
    