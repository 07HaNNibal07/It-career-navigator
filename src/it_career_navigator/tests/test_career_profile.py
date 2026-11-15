import pytest
from sqlalchemy import select

from it_career_navigator.auth import create_access_token
from it_career_navigator.models import Skill, User

pytestmark = pytest.mark.anyio
PREFIX = "/users/career_profile"


@pytest.fixture
async def career_user(db_session):
    user = User(name="Career", surname="User", email="career@test.com", age=20,
                phone="+78005553535", password="unused")
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
def headers(career_user):
    return {"Authorization": "Bearer " + create_access_token({"sub": str(career_user.id)})}


async def test_preferences_partial_updates_and_validation(client, headers):
    response = await client.get(PREFIX, headers=headers)
    assert response.status_code == 200
    assert response.json()["experiences"] == []
    response = await client.patch(PREFIX, headers=headers, json={
        "desired_position": "Python Developer", "city": "Москва",
        "work_formats": ["remote", "remote"], "employment_types": ["full_time"],
    })
    assert response.json()["work_formats"] == ["remote"]
    response = await client.patch(PREFIX, headers=headers, json={"city": None})
    assert response.json()["city"] is None
    assert response.json()["desired_position"] == "Python Developer"
    assert response.json()["work_formats"] == ["remote"]
    assert (await client.patch(PREFIX, headers=headers, json={"work_formats": ["invalid"]})).status_code == 422
    assert (await client.patch(PREFIX, headers=headers, json={"work_formats": None})).status_code == 422


async def test_experience_crud_and_merged_dates(client, headers):
    response = await client.post(PREFIX + "/experiences", headers=headers, json={
        "position": "Backend Developer", "organization": "Example",
        "start_date": "2024-01-01", "end_date": "2024-12-31",
        "description": "Разработка API", "achievements": "Запустил сервис",
    })
    assert response.status_code == 201, response.text
    record_id = response.json()["id"]
    url = f"{PREFIX}/experiences/{record_id}"
    invalid = await client.patch(url, headers=headers, json={"end_date": "2023-01-01"})
    assert invalid.status_code == 422
    assert (await client.patch(url, headers=headers, json={"start_date": None})).status_code == 422
    changed = await client.patch(url, headers=headers, json={"end_date": None})
    assert changed.status_code == 200
    assert changed.json()["end_date"] is None
    assert changed.json()["position"] == "Backend Developer"
    assert len((await client.get(PREFIX + "/experiences", headers=headers)).json()) == 1
    assert (await client.delete(url, headers=headers)).status_code == 204
    assert (await client.get(PREFIX + "/experiences", headers=headers)).json() == []


async def test_project_catalog_skills_and_partial_update(client, headers, db_session):
    skill = Skill(name="Python")
    db_session.add(skill)
    await db_session.commit()
    response = await client.post(PREFIX + "/projects", headers=headers, json={
        "name": "Navigator", "role": "Автор", "description": "Диплом",
        "url": "https://example.com/project", "skill_ids": [skill.id, skill.id],
    })
    assert response.status_code == 201, response.text
    project_id = response.json()["id"]
    assert response.json()["skill_ids"] == [skill.id]
    url = f"{PREFIX}/projects/{project_id}"
    invalid = await client.patch(url, headers=headers, json={"skill_ids": [999999]})
    assert invalid.status_code == 422
    assert (await client.patch(url, headers=headers, json={"url": "javascript:alert(1)"})).status_code == 422
    response = await client.patch(url, headers=headers, json={"role": "Backend", "url": None})
    assert response.status_code == 200
    assert response.json()["skill_ids"] == [skill.id]
    assert response.json()["url"] is None
    assert (await client.get(PREFIX + "/projects", headers=headers)).json()[0]["role"] == "Backend"
    assert (await client.delete(url, headers=headers)).status_code == 204


@pytest.mark.parametrize("resource,payload", [
    ("experiences", {"position": "Dev", "organization": "Example", "start_date": "2024-01-01"}),
    ("projects", {"name": "Demo", "role": "Автор"}),
])
async def test_records_cannot_be_changed_by_another_user(client, headers, db_session, resource, payload):
    created = await client.post(f"{PREFIX}/{resource}", headers=headers, json=payload)
    record_id = created.json()["id"]
    other = User(name="Other", surname="User", email="other@test.com", age=20, phone="1", password="unused")
    db_session.add(other)
    await db_session.commit()
    other_headers = {"Authorization": "Bearer " + create_access_token({"sub": str(other.id)})}
    url = f"{PREFIX}/{resource}/{record_id}"
    assert (await client.patch(url, headers=other_headers, json={})).status_code == 404
    assert (await client.delete(url, headers=other_headers)).status_code == 404
    assert (await client.get(f"{PREFIX}/{resource}", headers=other_headers)).json() == []


async def test_career_api_requires_authentication(client):
    assert (await client.get(PREFIX)).status_code == 401
    assert (await client.post(PREFIX + "/projects", json={"name": "Demo", "role": "Автор"})).status_code == 401
    assert (await client.post("/profile/preferences", data={})).status_code == 303


async def test_project_skill_names_reuse_catalog_alias_and_create_missing(client, headers, db_session):
    from it_career_navigator.models import SkillAlias, UserSkill
    python = Skill(name="Python")
    postgres = Skill(name="PostgreSQL")
    db_session.add_all([python, postgres])
    await db_session.flush()
    db_session.add(SkillAlias(alias="Postgres", skill_id=postgres.id))
    await db_session.commit()
    response = await client.post(PREFIX + "/projects", headers=headers, json={
        "name": "Demo", "role": "Автор", "skill_ids": [python.id],
        "skill_names": ["python", "  Django  ", "django", "POSTGRES"],
    })
    assert response.status_code == 201, response.text
    skills = (await db_session.scalars(select(Skill))).all()
    assert sorted(skill.name for skill in skills) == ["Django", "PostgreSQL", "Python"]
    assert set(response.json()["skill_ids"]) == {skill.id for skill in skills}
    assert (await db_session.scalars(select(UserSkill))).all() == []
    project_id = response.json()["id"]
    # Editing unrelated fields preserves the saved skill selection.
    response = await client.patch(f"{PREFIX}/projects/{project_id}", headers=headers, json={"name": "Renamed"})
    assert len(response.json()["skill_ids"]) == 3
    # Explicit replacement clears skills; adding a name reuses the existing catalog entry.
    response = await client.patch(f"{PREFIX}/projects/{project_id}", headers=headers, json={"skill_ids": [], "skill_names": ["Django"]})
    assert response.json()["skill_ids"] == [next(skill.id for skill in skills if skill.name == "Django")]


@pytest.mark.parametrize("names", [["   "], ["x" * 51], ["Python"] * 101])
async def test_invalid_project_skill_names_do_not_create_project(client, headers, names):
    response = await client.post(PREFIX + "/projects", headers=headers, json={
        "name": "Invalid", "role": "Автор", "skill_names": names,
    })
    assert response.status_code == 422
    assert (await client.get(PREFIX + "/projects", headers=headers)).json() == []


async def test_browser_session_cannot_modify_another_users_records(client, headers, db_session):
    experience = (await client.post(PREFIX + "/experiences", headers=headers, json={
        "position": "Dev", "organization": "Example", "start_date": "2024-01-01",
    })).json()
    project = (await client.post(PREFIX + "/projects", headers=headers, json={
        "name": "Owner project", "role": "Автор",
    })).json()
    await client.post("/register", data={"name": "Another", "surname": "User",
        "email": "other-page@test.com", "age": "20", "phone": "1", "password": "strong-password-123"})
    await client.post("/login", data={"email": "other-page@test.com", "password": "strong-password-123"})
    for resource, record in [("experiences", experience), ("projects", project)]:
        url = f"/profile/{resource}/{record['id']}"
        assert (await client.post(url, data={})).status_code == 404
        assert (await client.post(url + "/delete")).status_code == 404
    # Failed form submissions did not change the owner's stored records.
    assert len((await client.get(PREFIX + "/experiences", headers=headers)).json()) == 1
    assert len((await client.get(PREFIX + "/projects", headers=headers)).json()) == 1


async def test_browser_forms_render_save_edit_and_delete(client, db_session):
    await client.post("/register", data={"name": "Page", "surname": "User", "email": "career-page@test.com",
        "age": "20", "phone": "1", "password": "strong-password-123"})
    await client.post("/login", data={"email": "career-page@test.com", "password": "strong-password-123"})
    response = await client.post("/profile/preferences", data={
        "desired_position": "Python Developer", "city": "Москва", "work_formats": "remote",
    })
    assert response.status_code == 303
    response = await client.post("/profile/experiences", data={
        "position": "Разработчик", "organization": "Example", "start_date": "2024-01-01", "end_date": "",
    })
    assert response.status_code == 303
    invalid = await client.post("/profile/experiences", data={
        "position": "Разработчик", "organization": "Example", "start_date": "2024-01-01", "end_date": "2023-01-01",
    })
    assert invalid.status_code == 422
    assert "Не удалось сохранить" in invalid.text
    response = await client.post("/profile/projects", data={
        "name": "Мой проект", "role": "Автор", "description": "<script>alert(1)</script>", "url": "",
        "skill_names": "Django",
    })
    assert response.status_code == 303
    profile = await client.get("/profile")
    assert profile.status_code == 200
    assert "Python Developer" in profile.text
    assert "Мой проект" in profile.text
    assert "&lt;script&gt;" in profile.text
    assert 'data-name="Django"' in profile.text
    from it_career_navigator.models import UserExperience, UserProject
    experience = (await db_session.scalars(select(UserExperience))).one()
    project = (await db_session.scalars(select(UserProject))).one()
    assert (await client.post(f"/profile/projects/{project.id}", data={"name": "Изменённый", "role": "Backend"})).status_code == 303
    assert (await client.post(f"/profile/experiences/{experience.id}", data={"position": "Dev", "organization": "Example", "start_date": "2024-02-01"})).status_code == 303
    assert (await client.post(f"/profile/projects/{project.id}/delete")).status_code == 303
    assert (await client.post(f"/profile/experiences/{experience.id}/delete")).status_code == 303
