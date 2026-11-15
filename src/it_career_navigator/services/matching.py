import calendar
from datetime import UTC, date, datetime, timedelta
import logging

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from it_career_navigator.models import (
    Direction, Skill, UserSkill, Vacancy, VacancyMatch,
    VacancyRequirement, VacancySearch,
)
from it_career_navigator.services.career_profile import get_profile, get_user

logger = logging.getLogger(__name__)


def experience_months(periods, as_of: date) -> int | None:
    """Union inclusive work periods; count calendar months and remaining day fractions.

    Missing employment history means unknown, not zero. Projects are excluded.
    """
    intervals = sorted((start, min(end or as_of, as_of) + timedelta(days=1))
                       for start, end in periods if start <= as_of)
    if not intervals:
        return None
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    months = 0.0
    for start, end in merged:
        whole = (end.year - start.year) * 12 + end.month - start.month
        def anniversary(n):
            year, month = divmod(start.year * 12 + start.month - 1 + n, 12)
            return date(year, month + 1, min(start.day, calendar.monthrange(year, month + 1)[1]))
        if anniversary(whole) > end:
            whole -= 1
        months += whole + (end - anniversary(whole)).days / 30.4375
    return int(months)


def evaluate_requirements(requirements, user_skill_ids, available_months, required_months):
    matched = [item for item in requirements if item["id"] in user_skill_ids]
    missing = [item for item in requirements if item["id"] not in user_skill_ids]
    if not requirements:
        return None, None, None, matched, missing, [
            "Требования вакансии ещё не разобраны. Соответствие не оценено."
        ]
    weight = lambda item: 2 if item["is_required"] else 1
    skill_score = 100 * sum(map(weight, matched)) / sum(map(weight, requirements))
    reasons = [f"Совпало навыков: {len(matched)} из {len(requirements)}. Обязательные требования имеют двойной вес."]
    if required_months == 0:
        exp_score = 100.0
        reasons.append("В вакансии явно указано: опыт не требуется.")
    elif required_months is None or available_months is None:
        exp_score = None
        reasons.append("Опыт не оценён: недостаточно данных в профиле или вакансии. Балл рассчитан только по навыкам.")
    else:
        exp_score = min(available_months / required_months, 1) * 100
        reasons.append(f"Общий стаж: {available_months} мес.; требуется от {required_months} мес. Релевантность должностей отдельно не оценивалась.")
    score = skill_score if exp_score is None else .8 * skill_score + .2 * exp_score
    return round(score, 2), round(skill_score, 2), (round(exp_score, 2) if exp_score is not None else None), matched, missing, reasons


async def create_search(user_id, data, db):
    user = await get_user(user_id, db)
    profile = await get_profile(user_id, db)
    filters = {
        "desired_position": user.desired_position, "direction_id": user.direction_id,
        "target_level": user.target_level, "city": user.city,
        "work_formats": user.work_formats, "employment_types": user.employment_types,
        "include_unknown_conditions": True,
    } | data.model_dump(exclude_unset=True)
    if filters["direction_id"] is not None and await db.get(Direction, filters["direction_id"]) is None:
        raise HTTPException(422, "Направление не найдено.")
    skill_rows = (await db.execute(
        select(Skill.id, Skill.name, UserSkill.proficiency_level)
        .join(UserSkill, UserSkill.skill_id == Skill.id).where(UserSkill.user_id == user_id)
    )).all()
    today = datetime.now(UTC).date()
    available_months = experience_months([(item.start_date, item.end_date) for item in profile.experiences], today)
    snapshot = profile.model_dump(mode="json") | {
        "skills": [{"id": row.id, "name": row.name, "proficiency_level": row.proficiency_level} for row in skill_rows],
        "experience_months": available_months, "as_of": today.isoformat(),
        "direction_id": user.direction_id, "target_level": user.target_level,
    }
    search = VacancySearch(user_id=user_id, filters=filters, profile_snapshot=snapshot,
                           status="running", created_at=datetime.now(UTC))
    db.add(search)
    await db.commit()
    search_id = search.id
    try:
        query = select(Vacancy).options(
            selectinload(Vacancy.requirements).selectinload(VacancyRequirement.skill)
        )
        if filters["desired_position"]:
            query = query.where(Vacancy.title.icontains(filters["desired_position"], autoescape=True))
        # Missing direction/level is eligible only when no filter for that field is set.
        if filters["direction_id"] is not None:
            query = query.where(Vacancy.direction_id == filters["direction_id"])
        if filters["target_level"]:
            query = query.where(func.lower(Vacancy.level) == filters["target_level"].lower())
        for column, value in [(Vacancy.city, filters["city"]),
                              (Vacancy.work_format, filters["work_formats"]),
                              (Vacancy.employment_type, filters["employment_types"])]:
            if not value:
                continue
            condition = column.in_(value) if isinstance(value, list) else func.lower(column) == value.lower()
            if filters["include_unknown_conditions"]:
                condition = or_(condition, column.is_(None))
            query = query.where(condition)
        candidates = (await db.scalars(query)).all()
        ids = {row.id for row in skill_rows}
        for vacancy in candidates:
            requirements = sorted([
                {"id": item.skill_id, "name": item.skill.name, "is_required": item.is_required}
                for item in vacancy.requirements
            ], key=lambda item: (not item["is_required"], item["name"].casefold()))
            score, skill_score, exp_score, matched, missing, reasons = evaluate_requirements(
                requirements, ids, available_months, vacancy.min_experience_months,
            )
            if missing:
                reasons.append("Недостающие навыки: " + ", ".join(item["name"] for item in missing) + ".")
            for field, label in [("city", "Город"), ("work_format", "Формат работы"), ("employment_type", "Занятость")]:
                if getattr(vacancy, field) is None:
                    reasons.append(f"{label}: не указано.")
            supporting = [project.name for project in profile.projects if set(project.skill_ids) & {item["id"] for item in matched}]
            if supporting:
                reasons.append("Совпавшие навыки встречаются в проектах: " + ", ".join(supporting) + ". Учебные проекты не увеличивают стаж.")
            vacancy_snapshot = {key: getattr(vacancy, key) for key in (
                "title", "company", "description", "source", "external_id", "url",
                "direction_id", "level", "city", "work_format", "employment_type", "min_experience_months",
            )}
            vacancy_snapshot["published_at"] = vacancy.published_at.isoformat() if vacancy.published_at else None
            vacancy_snapshot["requirements"] = requirements
            db.add(VacancyMatch(search_id=search_id, vacancy_id=vacancy.id, vacancy_snapshot=vacancy_snapshot,
                                score=score, skill_score=skill_score, experience_score=exp_score,
                                matched_skills=matched, missing_skills=missing, explanation=reasons,
                                published_at=vacancy.published_at))
        search.status = "completed"
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Vacancy search %s failed", search_id)
        search = await db.get(VacancySearch, search_id)
        search.status = "failed"
        search.error_message = "Не удалось завершить подбор. Попробуй создать новый запуск."
        await db.commit()
    return search


async def get_search(user_id, search_id, db):
    await get_user(user_id, db)
    search = (await db.scalars(select(VacancySearch).where(
        VacancySearch.id == search_id, VacancySearch.user_id == user_id,
    ))).one_or_none()
    if search is None:
        raise HTTPException(404, "Подбор не найден.")
    return search


async def search_results(user_id, search_id, db, offset=0, limit=20):
    search = await get_search(user_id, search_id, db)
    total = await db.scalar(select(func.count(VacancyMatch.id)).where(VacancyMatch.search_id == search_id))
    matches = (await db.scalars(select(VacancyMatch).where(VacancyMatch.search_id == search_id)
        .order_by(VacancyMatch.score.desc().nulls_last(), VacancyMatch.published_at.desc().nulls_last(), VacancyMatch.id)
        .offset(offset).limit(limit))).all()
    return {"search": search, "total": total, "matches": matches}


async def get_match(user_id, match_id, db):
    await get_user(user_id, db)
    match = (await db.scalars(select(VacancyMatch).join(VacancySearch)
        .where(VacancyMatch.id == match_id, VacancySearch.user_id == user_id))).one_or_none()
    if match is None:
        raise HTTPException(404, "Результат подбора не найден.")
    return match
