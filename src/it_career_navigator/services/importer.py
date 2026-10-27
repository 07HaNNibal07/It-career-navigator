from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from it_career_navigator.models import Direction, Skill, Vacancy, VacancyRequirement
from it_career_navigator.schemas import (
    ImportResult,
    VacancyImportItem,
)

async def import_vacancies(
    items: list[VacancyImportItem],
    db: AsyncSession,
) -> ImportResult:
    result = ImportResult()

    for item in items:
        existing_vacancy = await db.execute(
            select(Vacancy).where(
                Vacancy.source == item.source,
                Vacancy.external_id == item.external_id,
            )
        )

        if existing_vacancy.scalar_one_or_none():
            result.skipped_duplicates += 1
            continue
        
        direction_result = await db.execute(
            select(Direction).where(
                Direction.name == item.direction_name
            )
        )
        direction = direction_result.scalar_one_or_none()

        if direction is None:
            result.errors.append(f"Direction not found: {item.direction_name}")
            continue

        new_vacancy = Vacancy(
            source=item.source,
            external_id=item.external_id,
            title=item.title,
            company=item.company,
            url=item.url,
            description=item.description,
            level=item.level,
            published_at=item.published_at,
            direction_id=direction.id
        )

        db.add(new_vacancy)
        await db.flush()

        for requirement in item.requirements:
            skill_result = await db.execute(
                select(Skill).where(
                    Skill.name == requirement.name
                )
            )
            skill = skill_result.scalar_one_or_none()

            if skill is None:
                skill = Skill(name=requirement.name)
                db.add(skill)
                await db.flush()

            new_requirement = VacancyRequirement(
                vacancy_id=new_vacancy.id,
                skill_id=skill.id,
                is_required=requirement.is_required,
            )
            db.add(new_requirement)

            result.created_requirements += 1
        
        result.created_vacancies += 1

    await db.commit()
    return result