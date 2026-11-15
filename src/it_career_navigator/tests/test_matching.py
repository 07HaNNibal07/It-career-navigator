from datetime import date, datetime, UTC

import pytest
from sqlalchemy import delete, select

from it_career_navigator.auth import create_access_token, hash_password
from it_career_navigator.models import (
    Skill, User, UserExperience, UserSkill, Vacancy, VacancyMatch, VacancyRequirement, VacancySearch,
)
from it_career_navigator.services.matching import evaluate_requirements, experience_months


def test_experience_merges_overlaps_and_excludes_future():
    periods = [(date(2022, 1, 1), date(2022, 12, 31)),
               (date(2022, 6, 1), date(2023, 12, 31))]
    assert experience_months(periods, date(2024, 1, 1)) == 24
    assert experience_months([(date(2024, 1, 1), None)], date(2024, 12, 31)) == 12
    assert experience_months([], date(2024, 1, 1)) is None
    assert experience_months([(date(2030, 1, 1), None)], date(2024, 1, 1)) is None


def test_weighted_skills_experience_and_unknown_requirements():
    requirements = [{"id": 1, "name": "Python", "is_required": True},
                    {"id": 2, "name": "Docker", "is_required": False}]
    score, skills, experience, matched, missing, _ = evaluate_requirements(requirements, {1}, 6, 12)
    assert (score, skills, experience) == (63.33, 66.67, 50.0)
    assert matched[0]["name"] == "Python"
    assert missing[0]["name"] == "Docker"
    assert evaluate_requirements(requirements, {1}, None, 12)[:3] == (66.67, 66.67, None)
    assert evaluate_requirements(requirements, {1}, None, 0)[:3] == (73.33, 66.67, 100.0)
    assert evaluate_requirements(requirements, set(), None, None)[0] == 0
    assert evaluate_requirements([], {1}, 24, 12)[:3] == (None, None, None)


@pytest.fixture
async def matching_data(db_session):
    user = User(name="Match", surname="User", email="match@test.com", age=20, phone="1",
                password=hash_password("test-password-123"))
    python = Skill(name="Python")
    docker = Skill(name="Docker")
    db_session.add_all([user, python, docker])
    await db_session.flush()
    db_session.add(UserSkill(user_id=user.id, skill_id=python.id))
    first = Vacancy(source="demo", external_id="1", title="Python API", company="Example",
                    description="<script>bad()</script>", work_format="remote", level="Junior",
                    url="javascript:alert(1)", published_at=datetime(2025, 2, 1, tzinfo=UTC))
    second = Vacancy(source="demo", external_id="2", title="Python Backend", description="Docker required",
                     work_format="office", level="junior", city="Москва")
    unknown = Vacancy(source="demo", external_id="3", title="Unprocessed vacancy", description="Unknown")
    db_session.add_all([first, second, unknown])
    await db_session.flush()
    db_session.add_all([
        VacancyRequirement(vacancy_id=first.id, skill_id=python.id, is_required=True),
        VacancyRequirement(vacancy_id=first.id, skill_id=docker.id, is_required=False),
        VacancyRequirement(vacancy_id=second.id, skill_id=python.id, is_required=False),
        VacancyRequirement(vacancy_id=second.id, skill_id=docker.id, is_required=True),
    ])
    await db_session.commit()
    return user, first, second, unknown


def auth(user):
    return {"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})}


async def launch(client, headers, payload=None):
    response = await client.post("/users/vacancy_searches", headers=headers, json=payload or {})
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "completed"
    return response.json()["id"]


@pytest.mark.anyio
async def test_matching_ranks_paginates_and_preserves_snapshots(client, db_session, matching_data):
    user, first, second, unknown = matching_data
    headers = auth(user)
    search_id = await launch(client, headers)
    details_url = f"/users/vacancy_searches/{search_id}"
    result = (await client.get(details_url, headers=headers)).json()
    assert result["total"] == 3
    assert [item["score"] for item in result["matches"]] == [66.67, 33.33, None]
    assert [item["vacancy_id"] for item in result["matches"]] == [first.id, second.id, unknown.id]
    assert result["matches"][0]["missing_skills"][0]["name"] == "Docker"
    assert (await client.get(details_url + "?offset=1&limit=1", headers=headers)).json()["matches"][0]["vacancy_id"] == second.id
    original = result["matches"][0]
    match_id = original["id"]
    # Later changes cannot rewrite the evidence from an earlier search.
    user.desired_position = "Completely different"
    first.title = "Changed vacancy"
    python = (await db_session.scalars(select(Skill).where(Skill.name == "Python"))).one()
    python.name = "Renamed skill"
    await db_session.commit()
    saved = (await client.get(f"/users/vacancy_matches/{match_id}", headers=headers)).json()
    assert saved == original
    search = await db_session.get(VacancySearch, search_id)
    assert search.profile_snapshot["skills"][0]["name"] == "Python"
    assert "password" not in search.profile_snapshot
    assert "email" not in search.profile_snapshot
    assert len((await client.get("/users/vacancy_searches", headers=headers)).json()) == 1
    # Removing the source vacancy preserves its saved result.
    await db_session.execute(delete(Vacancy).where(Vacancy.id == first.id))
    await db_session.commit()
    db_session.expire_all()
    saved = (await client.get(f"/users/vacancy_matches/{match_id}", headers=headers)).json()
    assert saved["vacancy_id"] is None
    assert saved["vacancy_snapshot"]["title"] == "Python API"


@pytest.mark.anyio
async def test_filters_use_profile_and_can_be_overridden(client, db_session, matching_data):
    user, first, second, unknown = matching_data
    headers = auth(user)
    user.work_formats = ["remote"]
    await db_session.commit()
    search_id = await launch(client, headers)
    result = (await client.get(f"/users/vacancy_searches/{search_id}", headers=headers)).json()
    assert {item["vacancy_id"] for item in result["matches"]} == {first.id, unknown.id}
    search_id = await launch(client, headers, {"include_unknown_conditions": False, "target_level": "junior"})
    result = (await client.get(f"/users/vacancy_searches/{search_id}", headers=headers)).json()
    assert [item["vacancy_id"] for item in result["matches"]] == [first.id]
    search_id = await launch(client, headers, {"work_formats": [], "desired_position": "BACKEND"})
    assert (await client.get(f"/users/vacancy_searches/{search_id}", headers=headers)).json()["total"] == 1
    search_id = await launch(client, headers, {"desired_position": "%"})
    assert (await client.get(f"/users/vacancy_searches/{search_id}", headers=headers)).json()["total"] == 0
    response = await client.post("/users/vacancy_searches", headers=headers, json={"direction_id": 999999})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_known_experience_conditions_and_date_ties(client, db_session, matching_data):
    user, first, second, unknown = matching_data
    headers = auth(user)
    db_session.add_all([
        UserExperience(user_id=user.id, position="Dev", organization="One", start_date=date(2020, 1, 1), end_date=date(2020, 12, 31)),
        UserExperience(user_id=user.id, position="Dev", organization="Two", start_date=date(2020, 6, 1), end_date=date(2020, 12, 31)),
    ])
    first.min_experience_months = 24
    first.city = "Москва"
    first.employment_type = "full_time"
    second.employment_type = "part_time"
    await db_session.commit()
    search_id = await launch(client, headers, {"city": "москва", "employment_types": ["full_time"], "include_unknown_conditions": False})
    result = (await client.get(f"/users/vacancy_searches/{search_id}", headers=headers)).json()
    assert result["total"] == 1
    assert result["matches"][0]["score"] == 63.33
    assert result["matches"][0]["experience_score"] == 50
    assert (await db_session.get(VacancySearch, search_id)).profile_snapshot["experience_months"] == 12
    # Equal scores use publication date; missing publication dates follow dated entries.
    first.min_experience_months = None
    for requirement in (await db_session.scalars(select(VacancyRequirement).where(VacancyRequirement.vacancy_id == second.id))).all():
        requirement.is_required = requirement.skill_id == (await db_session.scalars(select(Skill).where(Skill.name == "Python"))).one().id
    first.published_at = None
    second.published_at = datetime(2024, 1, 1, tzinfo=UTC)
    await db_session.commit()
    search_id = await launch(client, headers)
    result = (await client.get(f"/users/vacancy_searches/{search_id}", headers=headers)).json()
    assert [item["vacancy_id"] for item in result["matches"]] == [second.id, first.id, unknown.id]


@pytest.mark.anyio
async def test_matching_owner_checks_and_browser_flow(client, db_session, matching_data):
    user, first, _, _ = matching_data
    headers = auth(user)
    assert (await client.get("/users/vacancy_searches")).status_code == 401
    assert (await client.post("/users/vacancy_searches", json={})).status_code == 401
    assert (await client.get("/vacancies")).status_code == 303
    search_id = await launch(client, headers)
    match_id = (await client.get(f"/users/vacancy_searches/{search_id}", headers=headers)).json()["matches"][0]["id"]
    other = User(name="Other", surname="User", email="other-match@test.com", age=20, phone="1", password="unused")
    db_session.add(other)
    await db_session.commit()
    for url in [f"/users/vacancy_searches/{search_id}", f"/users/vacancy_matches/{match_id}"]:
        assert (await client.get(url, headers=auth(other))).status_code == 404
    assert (await client.get("/users/vacancy_searches", headers=auth(other))).json() == []
    await client.post("/login", data={"email": "match@test.com", "password": "test-password-123"})
    assert (await client.get("/vacancies")).status_code == 200
    created = await client.post("/vacancies/searches", data={"include_unknown_conditions": "on"})
    assert created.status_code == 303
    assert (await client.get(created.headers["location"])).status_code == 200
    page = await client.get(f"/vacancies/matches/{match_id}")
    assert page.status_code == 200
    assert "&lt;script&gt;" in page.text
    assert 'href="javascript:' not in page.text
    # A session cannot bypass ownership even when a different JWT is supplied.
    foreign = await launch(client, auth(other))
    assert (await client.get(f"/vacancies/searches/{foreign}")).status_code == 404


@pytest.mark.anyio
async def test_failure_rolls_back_partial_matches_and_keeps_history(client, db_session, matching_data, monkeypatch):
    from it_career_navigator.services import matching
    original = matching.evaluate_requirements
    calls = 0
    def fail(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("internal diagnostic")
        return original(*args)
    monkeypatch.setattr(matching, "evaluate_requirements", fail)
    headers = auth(matching_data[0])
    response = await client.post("/users/vacancy_searches", headers=headers, json={})
    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert calls == 2
    assert "internal diagnostic" not in response.text
    assert (await db_session.scalars(select(VacancyMatch))).all() == []
    assert len((await client.get("/users/vacancy_searches", headers=headers)).json()) == 1
