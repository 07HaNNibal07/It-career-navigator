import pytest


DEFAULT_EMAIL = "ilgar@test.com"
DEFAULT_PASSWORD = "strong-password-123"


async def create_test_user(
    client,
    *,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
):
    response = await client.post(
        "/users/create_user",
        json={
            "name": "Ilgar",
            "surname": "Babaev",
            "email": email,
            "age": 20,
            "phone": "+78005553535",
            "password": password,
        },
    )

    assert response.status_code == 200
    return response


async def login_test_user(
    client,
    *,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
) -> str:
    response = await client.post(
        "/users/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    return response.json()["access_token"]


async def create_authenticated_headers(
    client,
    *,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
) -> dict[str, str]:
    await create_test_user(client, email=email, password=password)
    token = await login_test_user(client, email=email, password=password)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_me_requires_token(client):
    response = await client.get("/users/me")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_register_user(client):
    response = await create_test_user(client)

    assert response.json()["email"] == DEFAULT_EMAIL
    assert "password" not in response.json()


@pytest.mark.anyio
async def test_login_user(client):
    email = "login@test.com"
    await create_test_user(client, email=email)

    token = await login_test_user(client, email=email)

    assert token


@pytest.mark.anyio
async def test_read_current_user_with_token(client):
    headers = await create_authenticated_headers(client)

    response = await client.get("/users/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == DEFAULT_EMAIL


@pytest.mark.anyio
async def test_delete_user_with_token(client):
    headers = await create_authenticated_headers(client)

    response = await client.delete("/users/delete_user", headers=headers)

    assert response.status_code == 200
    assert response.json()["detail"] == "User deleted successfully"


@pytest.mark.anyio
async def test_add_skills_with_token(client):
    headers = await create_authenticated_headers(client)

    response = await client.post(
        "/users/add_skills",
        json=[
            {"name": "Python"},
            {"name": "FastAPI"},
        ],
        headers=headers,
    )

    assert response.status_code == 200
    assert any(skill["name"] == "Python" for skill in response.json()["skills"])
    assert any(skill["name"] == "FastAPI" for skill in response.json()["skills"])


@pytest.mark.anyio
async def test_delete_skill_with_token(client):
    headers = await create_authenticated_headers(
        client,
        email="delete-skill@test.com",
    )

    add_skill_response = await client.post(
        "/users/add_skills",
        json=[{"name": "Python"}],
        headers=headers,
    )
    assert add_skill_response.status_code == 200
    assert any(
        skill["name"] == "Python"
        for skill in add_skill_response.json()["skills"]
    )

    delete_response = await client.request(
        "DELETE",
        "/users/delete_skills",
        json=[{"name": "Python"}],
        headers=headers,
    )

    assert delete_response.status_code == 200
    assert not any(
        skill["name"] == "Python"
        for skill in delete_response.json()["skills"]
    )


@pytest.mark.anyio
async def test_update_user_with_token(client):
    headers = await create_authenticated_headers(client)

    response = await client.patch(
        "/users/update_user",
        json={
            "name": "Ilgar Updated",
            "surname": "Babaev Updated",
            "email": "ilgar_updated@test.com",
            "age": 21,
            "phone": "+78005553536",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Ilgar Updated"
    assert response.json()["surname"] == "Babaev Updated"
    assert response.json()["email"] == "ilgar_updated@test.com"
    assert response.json()["age"] == 21
    assert response.json()["phone"] == "+78005553536"


@pytest.mark.anyio
async def test_update_target_with_token(client):
    direction_response = await client.post(
        "/internal/create_directions",
        json={"name": "Python Backend"},
        headers={"X-Internal-API-Key": "test-internal-key"},
    )
    assert direction_response.status_code == 200

    headers = await create_authenticated_headers(client)

    response = await client.patch(
        "/users/update_target",
        json={
            "target_level": "Senior",
            "direction_id": direction_response.json()["id"],
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["target_level"] == "Senior"
    assert response.json()["direction_id"] == direction_response.json()["id"]


@pytest.mark.anyio
async def test_create_analysis_with_token(client):
    direction_response = await client.post(
        "/internal/create_directions",
        json={"name": "Python Backend"},
        headers={"X-Internal-API-Key": "test-internal-key"},
    )
    assert direction_response.status_code == 200

    headers = await create_authenticated_headers(client)

    response = await client.post(
        "/users/create_analysis",
        json={
            "direction_id": direction_response.json()["id"],
            "target_level": "Senior",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["direction_id"] == direction_response.json()["id"]
    assert response.json()["target_level"] == "Senior"
    assert response.json()["status"] == "queued"

@pytest.mark.anyio
async def test_run_analysis_with_token(client):
    direction_response = await client.post(
        "/internal/create_directions",
        json={"name": "Python Backend"},
        headers={"X-Internal-API-Key": "test-internal-key"},
    )
    assert direction_response.status_code == 200

    headers = await create_authenticated_headers(client)

    create_response = await client.post(
        "/users/create_analysis",
        json={
            "direction_id": direction_response.json()["id"],
            "target_level": "Senior",
        },
        headers=headers,
    )
    assert create_response.status_code == 200

    analysis_id = create_response.json()["id"]

    run_response = await client.post(
        "/users/run_analysis",
        params={"analysis_id": analysis_id},
        headers=headers,
    )
    assert run_response.status_code == 200
    assert run_response.json()["id"] == analysis_id
    assert run_response.json()["status"] == "completed"


@pytest.mark.anyio
async def test_get_analysis_statistics_with_token(client):
    direction_response = await client.post(
        "/internal/create_directions",
        json={"name": "Python Backend"},
        headers={"X-Internal-API-Key": "test-internal-key"},
    )
    assert direction_response.status_code == 200

    headers = await create_authenticated_headers(client)

    create_response = await client.post(
        "/users/create_analysis",
        json={
            "direction_id": direction_response.json()["id"],
            "target_level": "Senior",
        },
        headers=headers,
    )
    assert create_response.status_code == 200

    analysis_id = create_response.json()["id"]

    stats_response = await client.get(
        f"/users/analysis_statistics/{analysis_id}",
        headers=headers,
    )
    assert stats_response.status_code == 200
    assert isinstance(stats_response.json(), list)
    if stats_response.json():
        stat = stats_response.json()[0]
        assert "skill_name" in stat
        assert "vacancy_count" in stat
        assert "demand_percent" in stat