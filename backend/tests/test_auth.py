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


def test_users_cannot_see_each_others_data(client):
    alice = client.post(
        "/api/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "secret123"},
    ).json()
    alice_headers = {"Authorization": f"Bearer {alice['token']}"}
    alice_workspace = client.get("/api/workspaces", headers=alice_headers).json()["items"][0]

    uploaded = client.post(
        "/api/evidence/upload",
        files={"files": ("alice.txt", b"Alice private evidence", "text/plain")},
        headers=alice_headers,
    )
    evidence_id = uploaded.json()["items"][0]["id"]

    bob = client.post(
        "/api/auth/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "secret123"},
    ).json()
    bob_headers = {"Authorization": f"Bearer {bob['token']}"}
    bob_workspace = client.get("/api/workspaces", headers=bob_headers).json()["items"][0]

    assert alice_workspace["id"] != bob_workspace["id"]
    assert client.get("/api/evidence", headers=bob_headers).json()["items"] == []
    assert client.get(f"/api/evidence/{evidence_id}", headers=bob_headers).status_code == 404
    assert (
        client.patch(
            f"/api/workspaces/{alice_workspace['id']}",
            headers=bob_headers,
            json={"name": "hijacked"},
        ).status_code
        == 404
    )

    spoofed = client.get(
        "/api/evidence",
        headers={**bob_headers, "X-Workspace-Id": alice_workspace["id"]},
    )
    assert spoofed.json()["items"] == []

    alice_items = client.get("/api/evidence", headers=alice_headers).json()["items"]
    assert [item["name"] for item in alice_items] == ["alice.txt"]
