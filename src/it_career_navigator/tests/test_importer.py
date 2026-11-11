from it_career_navigator.services.importer import import_vacancies
from it_career_navigator.schemas import VacancyImportItem, ImportResult
from it_career_navigator.models import (
    Direction,
    Skill,
    SkillAlias,
    Vacancy,
    VacancyRequirement,
)
from sqlalchemy.ext.asyncio import AsyncSession

from it_career_navigator.schemas import (VacancyImportItem, ImportResult,RequirementImportItem)

import pytest
from sqlalchemy import select

from it_career_navigator.tests.conftest import db_session


@pytest.mark.anyio
async def test_import_vacancies(db_session: AsyncSession):
    
    direction = Direction(name="Python Backend")
    db_session.add(direction)
    await db_session.flush()
    
    items = [
        VacancyImportItem(
            source="source",
            external_id="external_id",
            title="title",
            company="company",
            url="url",
            description="description",
            level="level",
            direction_name="Python Backend",
            published_at="2024-06-01T00:00:00",
            requirements=[
                RequirementImportItem(
                    name="Python",
                    is_required=True
                ),
                RequirementImportItem(
                    name="Docker",
                    is_required=False
                )
            ]
        )
    ]
    
    result = await import_vacancies(items, db_session)
    
    assert isinstance(result, ImportResult)
    assert result.created_vacancies == 1
    assert result.skipped_duplicates == 0
    assert result.created_requirements == 2
    
    vacancy_result = await db_session.execute(select(Vacancy).where(Vacancy.external_id == "external_id"))
    vacancy = vacancy_result.scalar_one_or_none()
    
    assert vacancy.direction_id == direction.id
    
    
    duplicate_result = await import_vacancies(items, db_session)

    assert duplicate_result.created_vacancies == 0
    assert duplicate_result.skipped_duplicates == 1


@pytest.mark.anyio
async def test_import_vacancies_uses_skill_alias(db_session: AsyncSession):
    direction = Direction(name="Alias Python Backend")
    canonical_skill = Skill(name="PostgreSQL")
    db_session.add_all([direction, canonical_skill])
    await db_session.flush()

    alias = SkillAlias(alias="Postgres", skill_id=canonical_skill.id)
    db_session.add(alias)
    await db_session.flush()

    item = VacancyImportItem(
        source="alias-source",
        external_id="alias-001",
        title="Python Developer",
        description="Postgres required",
        direction_name=direction.name,
        requirements=[
            RequirementImportItem(name="Postgres", is_required=True),
        ],
    )

    result = await import_vacancies([item], db_session)
    assert result.created_vacancies == 1

    requirement_result = await db_session.execute(
        select(VacancyRequirement)
    )
    requirement = requirement_result.scalar_one()
    assert requirement.skill_id == canonical_skill.id
