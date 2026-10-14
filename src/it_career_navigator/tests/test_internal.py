import pytest


URL = "/internal/create_skills"
VALID_HEADERS = {
    "X-Internal-API-Key": "test-internal-key",
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