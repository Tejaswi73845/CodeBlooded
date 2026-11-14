from __future__ import annotations

from app.config import settings


def test_default_account_can_sign_in_and_out(client):
    login = client.post(
        "/api/auth/login",
        json={"email": settings.default_actor_email, "password": settings.default_password},
    )
    assert login.status_code == 200, login.text
    payload = login.json()
    token = payload["token"]
    assert payload["user"]["email"] == settings.default_actor_email

    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["name"] == settings.default_actor

    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert logout.json()["signedOut"] is True

    after = client.get("/api/auth/me", headers=headers)
    assert after.status_code == 401


def test_register_and_login_new_account(client):
    email = "new.analyst@example.com"
    created = client.post(
        "/api/auth/register",
        json={"name": "New Analyst", "email": email, "password": "secret123"},
    )
    assert created.status_code == 201, created.text
    token = created.json()["token"]
    assert created.json()["user"]["email"] == email

    duplicate = client.post(
        "/api/auth/register",
        json={"name": "New Analyst", "email": email, "password": "secret123"},
    )
    assert duplicate.status_code == 409

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200

    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})

    login = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert login.status_code == 200
    client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {login.json()['token']}"},
    )


def test_invalid_credentials_are_rejected(client):
    response = client.post(
        "/api/auth/login",
        json={"email": settings.default_actor_email, "password": "wrong-password"},
    )
    assert response.status_code == 401
