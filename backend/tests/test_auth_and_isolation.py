from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.auth_service import register_user
from tests.fixtures.sample_scholarships import seed_test_scholarships


def test_register_login_logout_and_me(client: TestClient) -> None:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "student1@example.com", "password": "StrongPassword123!", "full_name": "Asha"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "student1@example.com"
    assert r.json()["user"]["is_admin"] is False

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "student1@example.com"

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200

    me_after = client.get("/api/v1/auth/me")
    assert me_after.status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "STUDENT1@example.com", "password": "StrongPassword123!"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "student1@example.com"


def test_user_data_isolation_and_admin_authorization(
    client: TestClient, db_session: Session
) -> None:
    schols = seed_test_scholarships(db_session)

    # User A registers, saves, creates tracking record
    client.post(
        "/api/v1/auth/register",
        json={"email": "usera@example.com", "password": "Password1234!"},
    )
    save_r = client.post("/api/v1/saved", json={"scholarship_id": schols["stem"].id})
    assert save_r.status_code == 201
    app_r = client.post(
        "/api/v1/applications",
        json={"scholarship_id": schols["stem"].id, "status": "PREPARING", "notes": "Private note"},
    )
    assert app_r.status_code == 201
    app_id = app_r.json()["id"]

    # User A cannot access admin endpoints
    assert client.get("/api/v1/admin/sources").status_code == 403

    client.post("/api/v1/auth/logout")

    # User B registers and tries to read/modify User A's records
    client.post(
        "/api/v1/auth/register",
        json={"email": "userb@example.com", "password": "Password1234!"},
    )
    assert client.get("/api/v1/saved").json() == []
    assert client.get("/api/v1/applications").json() == []
    assert (
        client.patch(
            f"/api/v1/applications/{app_id}", json={"status": "SUBMITTED"}
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/applications/{app_id}").status_code == 404

    # Admin user can access admin endpoints
    register_user(
        db_session,
        email="admin@example.com",
        password="AdminPassword123!",
        full_name="Admin",
        is_admin=True,
    )
    client.post("/api/v1/auth/logout")
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPassword123!"},
    )
    assert client.get("/api/v1/admin/sources").status_code == 200
