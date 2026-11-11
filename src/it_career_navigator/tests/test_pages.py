import pytest


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
