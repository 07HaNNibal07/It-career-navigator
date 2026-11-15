import pytest
from sqlalchemy import func, select

from it_career_navigator.models import Skill, SkillAlias, User, UserSkill
from it_career_navigator.seed_skills import load_catalog, seed_catalog


@pytest.mark.anyio
async def test_seed_is_repeatable_and_preserves_existing_catalog_and_links(db_session):
    python = Skill(name="python")
    custom = Skill(name="Existing framework")
    user = User(name="Seed", surname="User", email="seed@test.com", age=20, phone="1", password="unused")
    db_session.add_all([python, custom, user])
    await db_session.flush()
    alias = SkillAlias(alias="Django", skill_id=custom.id)
    link = UserSkill(user_id=user.id, skill_id=python.id, proficiency_level="advanced")
    db_session.add_all([alias, link])
    await db_session.commit()

    first = await seed_catalog(db_session)
    await db_session.commit()
    count = await db_session.scalar(select(func.count(Skill.id)))
    assert first.catalog_size == len(load_catalog())
    assert count == first.created_skills + 2
    assert first.created_aliases > 0
    assert (await db_session.scalars(select(Skill).where(func.lower(Skill.name) == "python"))).one().id == python.id
    assert (await db_session.scalars(select(Skill).where(Skill.name == "Django"))).one_or_none() is None

    second = await seed_catalog(db_session)
    await db_session.commit()
    assert second.created_skills == 0
    assert second.created_aliases == 0
    assert await db_session.scalar(select(func.count(Skill.id))) == count
    assert (await db_session.get(UserSkill, link.id)).proficiency_level == "advanced"
    assert (await db_session.get(SkillAlias, alias.id)).skill_id == custom.id
    js = (await db_session.scalars(select(SkillAlias).where(SkillAlias.alias == "JS"))).one()
    assert (await db_session.get(Skill, js.skill_id)).name == "JavaScript"
