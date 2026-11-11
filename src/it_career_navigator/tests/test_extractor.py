import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from it_career_navigator.config import settings
from it_career_navigator.models import Vacancy, VacancyRequirement
from it_career_navigator.services.extractor import extract_vacancy_requirements


@pytest.mark.anyio
async def test_fallback_extracts_and_saves_requirements(
    db_session: AsyncSession,
    monkeypatch,
):
    monkeypatch.setattr(settings, "llm_base_url", None)
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.setattr(settings, "llm_model", None)

    vacancy = Vacancy(
        source="extractor-test",
        external_id="fallback-001",
        title="Python Developer",
        description=(
            "Required: Python and FastAPI. Docker will be a plus."
        ),
    )
    db_session.add(vacancy)
    await db_session.flush()

    result = await extract_vacancy_requirements(vacancy.id, db_session)

    assert result.extraction_method == "fallback"
    assert result.created_requirements == 3
    assert result.skipped_existing == 0

    requirements_by_name = {
        requirement.name: requirement
        for requirement in result.requirements
    }
    assert requirements_by_name["Python"].is_required is True
    assert requirements_by_name["FastAPI"].is_required is True
    assert requirements_by_name["Docker"].is_required is False

    saved_requirements = await db_session.execute(
        select(VacancyRequirement).where(
            VacancyRequirement.vacancy_id == vacancy.id
        )
    )
    assert len(saved_requirements.scalars().all()) == 3

    repeated_result = await extract_vacancy_requirements(
        vacancy.id,
        db_session,
    )
    assert repeated_result.created_requirements == 0
    assert repeated_result.skipped_existing == 3
