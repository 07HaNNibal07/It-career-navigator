from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from it_career_navigator.models import (
    Analysis,
    SkillStatistic,
    Vacancy,
    VacancyRequirement,
)


async def run_analysis(
    analysis_id: int,
    current_user_id: int,
    db: AsyncSession,
) -> list[SkillStatistic]:
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

    if analysis.status != "queued":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis has already been run",
        )

    analysis.status = "running"

    vacancies_query = select(Vacancy.id).where(
        Vacancy.direction_id == analysis.direction_id
    )

    if analysis.target_level is not None:
        vacancies_query = vacancies_query.where(
            Vacancy.level == analysis.target_level
        )

    vacancy_ids = list(
        (await db.execute(vacancies_query)).scalars().all()
    )
    total_vacancies = len(vacancy_ids)

    if total_vacancies == 0:
        analysis.status = "completed"
        await db.commit()
        return []

    statistics_result = await db.execute(
        select(
            VacancyRequirement.skill_id,
            func.count(
                func.distinct(VacancyRequirement.vacancy_id)
            ),
        )
        .where(VacancyRequirement.vacancy_id.in_(vacancy_ids))
        .group_by(VacancyRequirement.skill_id)
    )

    statistics = []

    for skill_id, vacancy_count in statistics_result.all():
        statistic = SkillStatistic(
            analysis_id=analysis.id,
            skill_id=skill_id,
            vacancy_count=vacancy_count,
            demand_percent=round(
                vacancy_count / total_vacancies * 100,
                2,
            ),
        )
        db.add(statistic)
        statistics.append(statistic)

    analysis.status = "completed"
    await db.commit()

    return statistics