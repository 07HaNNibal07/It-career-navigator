"""Populate the shared skill catalog: uv run python -m it_career_navigator.seed_skills."""
import asyncio
from dataclasses import dataclass
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from it_career_navigator.models import Skill, SkillAlias


ALIASES = {
    "Postgres": "PostgreSQL", "postgresql": "PostgreSQL",
    "JS": "JavaScript", "TS": "TypeScript", "Golang": "Go",
    "React.js": "React", "ReactJS": "React", "Vue": "Vue.js",
    "VueJS": "Vue.js", "NextJS": "Next.js", "NodeJS": "Node.js",
    "Node": "Node.js", "DRF": "Django REST Framework", "K8s": "Kubernetes",
    "sklearn": "scikit-learn", "Tensorflow": "TensorFlow",
    "HuggingFace Transformers": "Hugging Face Transformers",
    "BeautifulSoup": "Beautiful Soup", "BS4": "Beautiful Soup",
    "SQL Server": "Microsoft SQL Server", "MSSQL": "Microsoft SQL Server",
    "CSharp": "C#", "C sharp": "C#", "CPP": "C++",
    "Amazon Web Services": "AWS", "GCP": "Google Cloud",
    "Azure": "Microsoft Azure", "K8S": "Kubernetes", "Kafka": "Apache Kafka",
    "Spark": "Apache Spark", "Airflow": "Apache Airflow",
    "ReactNative": "React Native", "Tailwind": "Tailwind CSS",
    "MUI": "Material UI", "OOP": "Object-Oriented Programming",
    "DDD": "Domain-Driven Design", "REST": "REST API", "Oauth2": "OAuth 2.0",
}


@dataclass
class SeedResult:
    catalog_size: int
    created_skills: int
    created_aliases: int


def load_catalog() -> list[str]:
    groups = json.loads((Path(__file__).parent / "data" / "skills_catalog.json").read_text(encoding="utf-8"))
    names = [name for group in groups.values() for name in group]
    if any(not isinstance(name, str) or not name.strip() or len(name) > 50 or name != name.strip() for name in names):
        raise ValueError("Skill names must contain 1–50 characters without outer whitespace")
    normalized = [name.casefold() for name in names]
    if len(normalized) != len(set(normalized)):
        raise ValueError("Duplicate skill names in the catalog")
    return names


async def seed_catalog(db) -> SeedResult:
    """Add missing entries; keep existing skills, aliases and user links intact.

    The caller owns the transaction and commits the entire catalog together.
    """
    names = load_catalog()
    skills = {name.casefold(): skill_id for skill_id, name in (await db.execute(select(Skill.id, Skill.name))).all()}
    aliases = {name.casefold(): skill_id for name, skill_id in (await db.execute(select(SkillAlias.alias, SkillAlias.skill_id))).all()}
    to_create = [{"name": name} for name in names if name.casefold() not in skills and name.casefold() not in aliases]
    created_skills = 0
    if to_create:
        added = (await db.execute(
            insert(Skill).values(to_create).on_conflict_do_nothing(index_elements=["name"])
            .returning(Skill.id)
        )).all()
        created_skills = len(added)
    skills = {name.casefold(): skill_id for skill_id, name in (await db.execute(select(Skill.id, Skill.name))).all()}
    resolved = aliases | skills
    new_aliases = []
    for alias, canonical in ALIASES.items():
        key = alias.casefold()
        if key in resolved:
            continue
        new_aliases.append({"alias": alias, "skill_id": resolved[canonical.casefold()]})
        resolved[key] = resolved[canonical.casefold()]
    created_aliases = 0
    if new_aliases:
        created_aliases = len((await db.execute(
            insert(SkillAlias).values(new_aliases).on_conflict_do_nothing(index_elements=["alias"])
            .returning(SkillAlias.id)
        )).all())
    return SeedResult(len(names), created_skills, created_aliases)


async def main():
    from it_career_navigator.database import SessionLocal, engine
    try:
        async with SessionLocal() as db:
            async with db.begin():
                result = await seed_catalog(db)
            total = len((await db.execute(select(Skill.id))).all())
        print(f"Catalog: {result.catalog_size}; added skills: {result.created_skills}; "
              f"added aliases: {result.created_aliases}; total skills in DB: {total}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
