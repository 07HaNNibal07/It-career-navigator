import pytest
import json

from it_career_navigator.config import settings


URL = "/internal/create_skills"
VALID_HEADERS = {
    "X-Internal-API-Key": "test-internal-key",
}
VACANCY_URL = "/internal/create_vacancy"
VACANCY_FILE_URL = "/internal/import_vacancies_file"

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

@pytest.mark.anyio
async def test_create_skill_alias_with_valid_key(client):
    skill_response = await client.post(
        "/internal/create_skills",
        json={"name": "Python"},
        headers=VALID_HEADERS,
    )
    assert skill_response.status_code == 200

    response = await client.post(
        "/internal/create_skill_alias",
        json={
            "alias": "Py",
            "skill_id": skill_response.json()["id"],
        },
        headers=VALID_HEADERS,
    )

    duplicate_response = await client.post(
        "/internal/create_skill_alias",
        json={
            "alias": "Py",
            "skill_id": skill_response.json()["id"],
        },
        headers=VALID_HEADERS,
    )

    assert duplicate_response.status_code == 400
    assert duplicate_response.json()["detail"] == "Skill alias already exists"

    assert response.status_code == 200
    assert response.json()["alias"] == "Py"
    assert response.json()["skill_id"] == skill_response.json()["id"]
    
    
@pytest.mark.anyio
async def test_import_vacancies_without_key(client):
    response = await client.post(
        "/internal/import_vacancies",
        json=[],
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid internal API key"


@pytest.mark.anyio
async def test_import_vacancies_with_valid_key(client):
    direction_response = await client.post(
        "/internal/create_directions",
        json={"name": "Import Python Backend"},
        headers=VALID_HEADERS,
    )
    assert direction_response.status_code == 200

    vacancies = [
        {
            "source": "test_import",
            "external_id": "import-001",
            "title": "Junior Python Developer",
            "company": "Test Company",
            "url": "https://example.com/import-001",
            "description": "Python and Docker",
            "direction_name": "Import Python Backend",
            "level": "junior",
            "published_at": "2024-06-01T12:00:00Z",
            "requirements": [
                {"name": "Python", "is_required": True},
                {"name": "Docker", "is_required": False},
            ],
        }
    ]

    response = await client.post(
        "/internal/import_vacancies",
        json=vacancies,
        headers=VALID_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["created_vacancies"] == 1
    assert response.json()["created_requirements"] == 2
    assert response.json()["skipped_duplicates"] == 0
    assert response.json()["errors"] == []


@pytest.mark.anyio
async def test_import_vacancies_file_without_key(client):
    response = await client.post(
        VACANCY_FILE_URL,
        files={
            "file": (
                "vacancies.json",
                b"[]",
                "application/json",
            )
        },
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_import_json_vacancies_file_with_valid_key(client):
    direction_response = await client.post(
        "/internal/create_directions",
        json={"name": "File Python Backend"},
        headers=VALID_HEADERS,
    )
    assert direction_response.status_code == 200

    content = json.dumps(
        [
            {
                "source": "file_json",
                "external_id": "file-001",
                "title": "Python Developer",
                "description": "Python and Docker",
                "direction_name": "File Python Backend",
                "requirements": [
                    {"name": "Python", "is_required": True},
                ],
            },
            {
                "source": "file_json",
                "external_id": "file-invalid",
                "description": "This row has no title",
                "direction_name": "File Python Backend",
            },
        ]
    ).encode()

    response = await client.post(
        VACANCY_FILE_URL,
        files={
            "file": (
                "vacancies.json",
                content,
                "application/json",
            )
        },
        headers=VALID_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["created_vacancies"] == 1
    assert response.json()["created_requirements"] == 1
    assert len(response.json()["errors"]) == 1
    assert response.json()["errors"][0].startswith("Item 2:")


@pytest.mark.anyio
async def test_import_csv_vacancies_file_with_valid_key(client):
    direction_response = await client.post(
        "/internal/create_directions",
        json={"name": "CSV Python Backend"},
        headers=VALID_HEADERS,
    )
    assert direction_response.status_code == 200

    content = (
        'source,external_id,title,description,direction_name,requirements\n'
        'file_csv,file-001,Python Developer,Python and Docker,CSV Python Backend,"[{""name"": ""Docker"", ""is_required"": false}]"\n'
    ).encode()

    response = await client.post(
        VACANCY_FILE_URL,
        files={
            "file": (
                "vacancies.csv",
                content,
                "text/csv",
            )
        },
        headers=VALID_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["created_vacancies"] == 1
    assert response.json()["created_requirements"] == 1
    assert response.json()["errors"] == []


@pytest.mark.anyio
async def test_extract_vacancy_requirements_with_fallback(client, monkeypatch):
    monkeypatch.setattr(settings, "llm_base_url", None)
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.setattr(settings, "llm_model", None)

    vacancy_response = await client.post(
        VACANCY_URL,
        json={
            **VACANCY_DATA,
            "external_id": "extract-001",
            "description": "Python, FastAPI and Docker are required",
        },
        headers=VALID_HEADERS,
    )
    assert vacancy_response.status_code == 200

    response = await client.post(
        (
            "/internal/vacancies/"
            f"{vacancy_response.json()['id']}/extract_requirements"
        ),
        headers=VALID_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["extraction_method"] == "fallback"
    assert response.json()["created_requirements"] == 3
    assert {
        requirement["name"]
        for requirement in response.json()["requirements"]
    } == {"Python", "FastAPI", "Docker"}
