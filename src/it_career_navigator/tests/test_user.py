import pytest


@pytest.mark.anyio
async def test_me_requires_token(client):
    response = await client.get("/users/me")

    assert response.status_code == 401
    
@pytest.mark.anyio
async def test_register_user(client):
    response = await client.post(
        "/users/create_user",
        json={
            "name": "Ilgar",
            "surname": "Babaev",
            "email": "ilgar@test.com",
            "age": 20,
            "phone": "+78005553535",
            "password": "strong-password-123",
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "ilgar@test.com"
    assert "password" not in response.json()

@pytest.mark.anyio
async def test_login_user(client):
    email = "login@test.com"
    password = "strong-password-123"

    create_response = await client.post(
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
    assert create_response.status_code == 200

    response = await client.post(
        "/users/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.anyio
async def test_read_current_user_with_token(client):
    await client.post(
        "/users/create_user",
        json={
            "name": "Ilgar",
            "surname": "Babaev",
            "email": "ilgar@test.com",
            "age": 20,
            "phone": "+78005553535",
            "password": "strong-password-123",
        },
    )

    login_response = await client.post(
        "/users/login",
        data={
            "username": "ilgar@test.com",
            "password": "strong-password-123",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "ilgar@test.com"

@pytest.mark.anyio
async def test_delete_user_with_token(client):
    await client.post(
        "/users/create_user",
        json={
            "name": "Ilgar",
            "surname": "Babaev",
            "email": "ilgar@test.com",
            "age": 20,
            "phone": "+78005553535",
            "password": "strong-password-123",
        },
    )

    login_response = await client.post(
        "/users/login",
        data={
            "username": "ilgar@test.com",
            "password": "strong-password-123",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = await client.delete(
        "/users/delete_user",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["detail"] == "User deleted successfully"

@pytest.mark.anyio
async def test_add_skills_with_token(client):
    await client.post(
        "/users/create_user",
        json={
            "name": "Ilgar",
            "surname": "Babaev",
            "email": "ilgar@test.com",
            "age": 20,
            "phone": "+78005553535",
            "password": "strong-password-123",
        },
    )

    login_response = await client.post(
        "/users/login",
        data={
            "username": "ilgar@test.com",
            "password": "strong-password-123",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = await client.post(
        "/users/add_skills",
        json=[
            {"name": "Python"},
            {"name": "FastAPI"},
        ],
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert any(skill["name"] == "Python" for skill in response.json()["skills"])
    assert any(skill["name"] == "FastAPI" for skill in response.json()["skills"])

@pytest.mark.anyio
async def test_delete_skill_with_token(client):
    email = "delete-skill@test.com"
    password = "strong-password-123"

    create_response = await client.post(
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
    assert create_response.status_code == 200

    login_response = await client.post(
        "/users/login",
        data={
            "username": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    add_skill_response = await client.post(
        "/users/add_skills",
        json=[
            {"name": "Python"},
        ],
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
        json=[
            {"name": "Python"},
        ],
        headers=headers,
    )

    assert delete_response.status_code == 200
    assert not any(
        skill["name"] == "Python"
        for skill in delete_response.json()["skills"]
    )

@pytest.mark.anyio
async def test_update_user_with_token(client):
    await client.post(
        "/users/create_user",
        json={
            "name": "Ilgar",
            "surname": "Babaev",
            "email": "ilgar@test.com",
            "age": 20,
            "phone": "+78005553535",
            "password": "strong-password-123",
        },
    )

    login_response = await client.post(
        "/users/login",
        data={
            "username": "ilgar@test.com",
            "password": "strong-password-123",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = await client.patch(
        "/users/update_user",
        json={
            "name": "Ilgar Updated",
            "surname": "Babaev Updated",
            "email": "ilgar_updated@test.com",
            "age": 21,
            "phone": "+78005553536",
        },
        headers={"Authorization": f"Bearer {token}"},
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
        json={
            "name": "Python Backend",
        },
        headers={
            "X-Internal-API-Key": "test-internal-key",
        },
    )

    assert direction_response.status_code == 200

    direction_id = direction_response.json()["id"]

    create_response = await client.post(
        "/users/create_user",
        json={
            "name": "Ilgar",
            "surname": "Babaev",
            "email": "ilgar@test.com",
            "age": 20,
            "phone": "+78005553535",
            "password": "strong-password-123",
        },
    )
    assert create_response.status_code == 200

    login_response = await client.post(
        "/users/login",
        data={
            "username": "ilgar@test.com",
            "password": "strong-password-123",
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = await client.patch(
        "/users/update_target",
        json={
            "target_level": "Senior",
            "direction_id": direction_id,
        },
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.json()["target_level"] == "Senior"
    assert response.json()["direction_id"] == direction_id