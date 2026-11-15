import json

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from it_career_navigator.career_schemas import (
    CareerPreferencesUpdate, CareerProfileResponse, ExperienceCreate,
    ExperienceResponse, ProjectCreate, ProjectResponse,
)
from it_career_navigator.models import Skill, SkillAlias, User, UserExperience, UserProject


def validate(schema, data):
    """Shared validation for JSON and HTML forms, including partial updates."""
    try:
        return schema.model_validate(data)
    except ValidationError as error:
        raise HTTPException(422, detail=json.loads(error.json(include_context=False))) from error


async def get_user(user_id, db):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


def project_response(project):
    return ProjectResponse(
        id=project.id, name=project.name, description=project.description,
        role=project.role, url=project.url,
        skill_ids=[skill.id for skill in project.skills],
    )


async def get_profile(user_id, db):
    user = await get_user(user_id, db)
    experiences = (await db.scalars(
        select(UserExperience).where(UserExperience.user_id == user_id)
        .order_by(UserExperience.start_date.desc(), UserExperience.id.desc())
    )).all()
    projects = (await db.scalars(
        select(UserProject).options(selectinload(UserProject.skills))
        .where(UserProject.user_id == user_id).order_by(UserProject.id.desc())
    )).all()
    return CareerProfileResponse(
        desired_position=user.desired_position, city=user.city,
        work_formats=user.work_formats, employment_types=user.employment_types,
        experiences=[ExperienceResponse.model_validate(item) for item in experiences],
        projects=[project_response(item) for item in projects],
    )


async def save_preferences(user_id, data, db):
    user = await get_user(user_id, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    await db.commit()
    return await get_profile(user_id, db)


async def get_owned(model, item_id, user_id, db):
    await get_user(user_id, db)
    query = select(model).where(model.id == item_id, model.user_id == user_id)
    if model is UserProject:
        query = query.options(selectinload(UserProject.skills))
    item = (await db.scalars(query)).one_or_none()
    if item is None:
        raise HTTPException(404, "Record not found")
    return item


async def save_experience(user_id, data, db, item_id=None):
    await get_user(user_id, db)
    if item_id is None:
        item = UserExperience(user_id=user_id)
        values = validate(ExperienceCreate, data.model_dump()).model_dump()
    else:
        item = await get_owned(UserExperience, item_id, user_id, db)
        current = ExperienceResponse.model_validate(item).model_dump(exclude={"id"})
        values = validate(ExperienceCreate, current | data.model_dump(exclude_unset=True)).model_dump()
    for key, value in values.items():
        setattr(item, key, value)
    db.add(item)
    await db.commit()
    return ExperienceResponse.model_validate(item)


async def save_project(user_id, data, db, item_id=None):
    await get_user(user_id, db)
    if item_id is None:
        item = UserProject(user_id=user_id)
        values = validate(ProjectCreate, data.model_dump())
    else:
        item = await get_owned(UserProject, item_id, user_id, db)
        current = project_response(item).model_dump(exclude={"id"})
        values = validate(ProjectCreate, current | data.model_dump(exclude_unset=True))
    skills = (await db.scalars(select(Skill).where(Skill.id.in_(values.skill_ids)))).all()
    if len(skills) != len(values.skill_ids):
        raise HTTPException(422, "Один из выбранных навыков отсутствует в каталоге.")
    skills = list(skills)
    for name in dict.fromkeys(values.skill_names):
        skill = (await db.scalars(select(Skill).where(func.lower(Skill.name) == name.lower()))).first()
        if skill is None:
            skill = (await db.scalars(
                select(Skill).join(SkillAlias, SkillAlias.skill_id == Skill.id)
                .where(func.lower(SkillAlias.alias) == name.lower())
            )).first()
        if skill is None:
            skill = Skill(name=name)
            db.add(skill)
            await db.flush()
        if all(existing.id != skill.id for existing in skills):
            skills.append(skill)
    if len(skills) > 100:
        raise HTTPException(422, "В проекте можно указать не более 100 навыков.")
    for key, value in values.model_dump(exclude={"skill_ids", "skill_names", "url"}).items():
        setattr(item, key, value)
    item.url = str(values.url) if values.url else None
    item.skills = skills
    db.add(item)
    await db.commit()
    return project_response(item)


async def delete_record(model, item_id, user_id, db):
    item = await get_owned(model, item_id, user_id, db)
    await db.delete(item)
    await db.commit()
