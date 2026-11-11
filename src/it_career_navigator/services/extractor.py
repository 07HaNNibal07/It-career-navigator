import httpx
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from it_career_navigator.config import settings
from it_career_navigator.models import Skill, SkillAlias, Vacancy, VacancyRequirement
from it_career_navigator.schemas import (
    RequirementExtraction,
    RequirementImportItem,
    VacancyRequirementsExtractionResponse,
)


FALLBACK_SKILLS = {
    "python": "Python",
    "fastapi": "FastAPI",
    "sqlalchemy": "SQLAlchemy",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "docker": "Docker",
    "redis": "Redis",
    "celery": "Celery",
    "rabbitmq": "RabbitMQ",
    "kubernetes": "Kubernetes",
    "pytest": "Pytest",
    "git": "Git",
    "ci/cd": "CI/CD",
}

OPTIONAL_MARKERS = (
    "nice to have",
    "optional",
    "will be a plus",
    "будет плюсом",
    "желательно",
)


async def extract_vacancy_requirements(
    vacancy_id: int,
    db: AsyncSession,
) -> VacancyRequirementsExtractionResponse:
    vacancy_result = await db.execute(
        select(Vacancy).where(Vacancy.id == vacancy_id)
    )
    vacancy = vacancy_result.scalar_one_or_none()

    if vacancy is None:
        raise LookupError("Vacancy not found")

    requirements, extraction_method = await extract_requirements(
        vacancy.description
    )

    created_requirements = 0
    skipped_existing = 0

    for requirement in requirements:
        skill = await _find_or_create_skill(requirement.name, db)
        existing_requirement_result = await db.execute(
            select(VacancyRequirement).where(
                VacancyRequirement.vacancy_id == vacancy.id,
                VacancyRequirement.skill_id == skill.id,
            )
        )

        if existing_requirement_result.scalar_one_or_none():
            skipped_existing += 1
            continue

        db.add(
            VacancyRequirement(
                vacancy_id=vacancy.id,
                skill_id=skill.id,
                is_required=requirement.is_required,
            )
        )
        created_requirements += 1

    await db.commit()

    return VacancyRequirementsExtractionResponse(
        vacancy_id=vacancy.id,
        extraction_method=extraction_method,
        created_requirements=created_requirements,
        skipped_existing=skipped_existing,
        requirements=requirements,
    )


async def extract_requirements(
    description: str,
) -> tuple[list[RequirementImportItem], str]:
    if _llm_is_configured():
        try:
            return await _extract_requirements_with_llm(description), "llm"
        except (httpx.HTTPError, KeyError, TypeError, ValidationError, ValueError):
            pass

    return _extract_requirements_with_fallback(description), "fallback"


def _llm_is_configured() -> bool:
    return all(
        [
            settings.llm_base_url,
            settings.llm_api_key,
            settings.llm_model,
        ]
    )


async def _extract_requirements_with_llm(
    description: str,
) -> list[RequirementImportItem]:
    prompt = """Extract technical job requirements from the vacancy text.
Return JSON only, using exactly this shape:
{"requirements": [{"name": "Python", "is_required": true}]}
Include only technologies or tools. Set is_required to false only when the text
explicitly says that a skill is optional, nice to have, or a plus.

Vacancy text:
"""

    headers = {
        "Authorization": (
            "Bearer " + settings.llm_api_key.get_secret_value()
        ),
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You return valid JSON only."},
            {"role": "user", "content": prompt + description},
        ],
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("LLM response content must be text")

    return RequirementExtraction.model_validate_json(
        _remove_markdown_fence(content)
    ).requirements


def _extract_requirements_with_fallback(
    description: str,
) -> list[RequirementImportItem]:
    normalized_description = description.lower()
    requirements: list[RequirementImportItem] = []
    found_names: set[str] = set()

    for keyword, skill_name in FALLBACK_SKILLS.items():
        index = normalized_description.find(keyword)
        if index == -1 or skill_name in found_names:
            continue

        context = _sentence_containing(
            normalized_description,
            index,
        )
        is_optional = any(marker in context for marker in OPTIONAL_MARKERS)
        requirements.append(
            RequirementImportItem(
                name=skill_name,
                is_required=not is_optional,
            )
        )
        found_names.add(skill_name)

    return requirements


async def _find_or_create_skill(name: str, db: AsyncSession) -> Skill:
    skill_result = await db.execute(
        select(Skill).where(Skill.name == name)
    )
    skill = skill_result.scalar_one_or_none()

    if skill is not None:
        return skill

    alias_result = await db.execute(
        select(Skill)
        .join(SkillAlias, SkillAlias.skill_id == Skill.id)
        .where(SkillAlias.alias == name)
    )
    skill = alias_result.scalar_one_or_none()

    if skill is not None:
        return skill

    skill = Skill(name=name)
    db.add(skill)
    await db.flush()
    return skill


def _remove_markdown_fence(content: str) -> str:
    stripped_content = content.strip()
    if not stripped_content.startswith("```"):
        return stripped_content

    lines = stripped_content.splitlines()
    if len(lines) < 3 or not lines[-1].startswith("```"):
        raise ValueError("LLM returned an incomplete Markdown code fence")

    return "\n".join(lines[1:-1])


def _sentence_containing(text: str, position: int) -> str:
    sentence_start = max(
        text.rfind(".", 0, position),
        text.rfind(";", 0, position),
        text.rfind("\n", 0, position),
    ) + 1
    sentence_end_candidates = [
        end
        for separator in (".", ";", "\n")
        if (end := text.find(separator, position)) != -1
    ]
    sentence_end = min(sentence_end_candidates, default=len(text))
    return text[sentence_start:sentence_end]
