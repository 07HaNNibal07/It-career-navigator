import pytest


URL = "/internal/create_skills"
VALID_HEADERS = {
    "X-Internal-API-Key": "test-internal-key",
}
VACANCY_URL = "/internal/create_vacancy"

VACANCY_DATA = {
    "source": "demo_json",
    "external_id": "python-backend-001",
    "title": "Python Backend Developer",
    "company": "Demo Company",
    "url": "https://example.com/vacancies/1",
    "description": "Python, FastAPI, PostgreSQL, Docker",
    "level": "junior",
    "published_at": "2024-06-01T12:00:00Z",
}

@pytest.mark.anyio
async def test_create_internal_skill_without_key(client):
    response = await client.post(
        URL,
        json={"name": "InternalPython"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid internal API key"


@pytest.mark.anyio
async def test_create_internal_skill_with_wrong_key(client):
    response = await client.post(
        URL,
        json={"name": "InternalPython"},
        headers={
            "X-Internal-API-Key": "wrong-key",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid internal API key"


@pytest.mark.anyio
async def test_create_internal_skill_with_valid_key(client):
    response = await client.post(
        URL,
        json={"name": "InternalPython"},
        headers=VALID_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "InternalPython"
    assert "id" in response.json()
    
@pytest.mark.anyio
async def test_create_internal_direction_with_valid_key(client):
    response = await client.post(
        "/internal/create_directions",
        json={"name": "Python Backend"},
        headers=VALID_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Python Backend"
    assert "id" in response.json()

@pytest.mark.anyio
async def test_create_vacancy_without_key(client):
    response = await client.post(
        VACANCY_URL,
        json=VACANCY_DATA,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid internal API key"
    
    
@pytest.mark.anyio
async def test_create_duplicate_vacancy(client):
    first_response = await client.post(
        VACANCY_URL,
        json=VACANCY_DATA,
        headers=VALID_HEADERS,
    )

    assert first_response.status_code == 200
    assert first_response.json()["title"] == "Python Backend Developer"
    assert first_response.json()["published_at"] == "2024-06-01T12:00:00Z"
    
    duplicate_response = await client.post(
        VACANCY_URL,
        json=VACANCY_DATA,
        headers=VALID_HEADERS,
    )

    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"] == "Vacancy already exists"

@pytest.mark.anyio
async def test_create_vacancy_requirement_with_valid_key(client):
    skill_response = await client.post(
        "/internal/create_skills",
        json={"name": "RequirementPython"},
        headers=VALID_HEADERS,
    )
    assert skill_response.status_code == 200

    vacancy_response = await client.post(
        VACANCY_URL,
        json=VACANCY_DATA,
        headers=VALID_HEADERS,
    )
    assert vacancy_response.status_code == 200

    response = await client.post(
        "/internal/create_vacancy_requirement",
        json={
            "vacancy_id": vacancy_response.json()["id"],
            "skill_id": skill_response.json()["id"],
            "is_required": True,
        },
        headers=VALID_HEADERS,
    )

    duplicate_response = await client.post(
        "/internal/create_vacancy_requirement",
        json={
            "vacancy_id": vacancy_response.json()["id"],
            "skill_id": skill_response.json()["id"],
            "is_required": True,
        },
        headers=VALID_HEADERS,
    )

    assert duplicate_response.status_code == 400
    assert (
        duplicate_response.json()["detail"]
        == "Vacancy requirement already exists"
    )
    
    assert response.status_code == 200
    assert response.json()["vacancy_id"] == vacancy_response.json()["id"]
    assert response.json()["skill_id"] == skill_response.json()["id"]
    assert response.json()["is_required"] is True

@pytest.mark.anyio
async def test_create_vacancy_requirement_without_key(client):
    response = await client.post(
        "/internal/create_vacancy_requirement",
        json={"vacancy_id": 1, "skill_id": 1, "is_required": True},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid internal API key"

