from it_career_navigator.services.importer import import_vacancies
from it_career_navigator.schemas import VacancyImportItem, ImportResult
from it_career_navigator.models import Vacancy, Direction
from sqlalchemy.ext.asyncio import AsyncSession

import pytest

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
        )
    ]
    
    result = await import_vacancies(items, db_session)
    
    assert isinstance(result, ImportResult)
    assert result.created_vacancies == 1
    assert result.skipped_duplicates == 0

    from sqlalchemy import select
    vacancy_result = await db_session.execute(select(Vacancy).where(Vacancy.external_id == "external_id"))
    vacancy = vacancy_result.scalar_one_or_none()
    
    assert vacancy.direction_id == direction.id
    
    
    duplicate_result = await import_vacancies(items, db_session)

    assert duplicate_result.created_vacancies == 0
    assert duplicate_result.skipped_duplicates == 1