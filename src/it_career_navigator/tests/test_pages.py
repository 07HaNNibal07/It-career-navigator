import pytest

from it_career_navigator.models import Skill


@pytest.mark.anyio
async def test_home_page(client):
    response = await client.get("/")

    assert response.status_code == 200
    assert "IT Career Navigator" in response.text


@pytest.mark.anyio
async def test_register_login_and_open_profile(client):
    register_response = await client.post(
        "/register",
        data={
            "name": "Page",
            "surname": "User",
            "email": "page-user@test.com",
            "age": "20",
            "phone": "+78005553535",
            "password": "strong-password-123",
        },
        follow_redirects=False,
    )
    assert register_response.status_code == 303
    assert register_response.headers["location"] == "/login"

    login_response = await client.post(
        "/login",
        data={
            "email": "page-user@test.com",
            "password": "strong-password-123",
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/profile"

    profile_response = await client.get("/profile")
    assert profile_response.status_code == 200
    assert "Page User" in profile_response.text


@pytest.mark.anyio
async def test_skill_search_returns_matching_catalog_skills(client, db_session):
    await client.post(
        "/register",
        data={
            "name": "Search",
            "surname": "User",
            "email": "search-user@test.com",
            "age": "20",
            "phone": "+78005553535",
            "password": "strong-password-123",
        },
    )
    await client.post(
        "/login",
        data={"email": "search-user@test.com", "password": "strong-password-123"},
    )
    fastapi = Skill(name="FastAPI")
    python = Skill(name="Python")
    db_session.add_all([fastapi, python])
    await db_session.commit()

    response = await client.get("/profile/skills/search", params={"query": "Fa"})

    assert response.status_code == 200
    assert response.json() == [{"id": fastapi.id, "name": "FastAPI"}]
