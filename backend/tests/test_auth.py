"""Test autentikasi & otorisasi (Bagian 18)."""

import pytest

from conftest import token_untuk

ENDPOINT_TERLINDUNGI = [
    ("post", "/chat", {"json": {"session_id": "s", "message": "hai"}}),
    ("get", "/chat/history?session_id=s", {}),
    ("post", "/documents", {"json": {"filename": "a.txt", "content": "isi"}}),
    ("get", "/auth/me", {}),
]


def test_health_publik(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("method,path", [(m, p) for m, p, _ in ENDPOINT_TERLINDUNGI])
def test_tanpa_token_ditolak(client, method, path):
    res = getattr(client, method)(path)
    assert res.status_code == 401


def test_login_berhasil(client, admin):
    res = client.post("/auth/login", data={"username": "admin_test", "password": "sandi12345"})
    assert res.status_code == 200
    body = res.json()
    assert body["role"] == "ADMIN"
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_password_salah(client, admin):
    res = client.post("/auth/login", data={"username": "admin_test", "password": "salah"})
    assert res.status_code == 401


def test_login_user_tidak_ada(client):
    res = client.post("/auth/login", data={"username": "hantu", "password": "apa saja"})
    assert res.status_code == 401


def test_token_palsu_ditolak(client):
    res = client.get("/auth/me", headers={"Authorization": "Bearer bukan.token.valid"})
    assert res.status_code == 401


def test_me_mengembalikan_identitas(client, header_admin):
    body = client.get("/auth/me", headers=header_admin).json()
    assert body["username"] == "admin_test"
    assert body["role"] == "ADMIN"
    assert body["is_active"] is True


def test_user_nonaktif_ditolak(client, user_biasa):
    from database import SessionLocal
    from models import User

    token = token_untuk(client, "user_test")

    db = SessionLocal()
    try:
        db.query(User).filter(User.username == "user_test").update({"is_active": False})
        db.commit()
    finally:
        db.close()

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


# --- Role-based access control ------------------------------------------------

def test_readonly_boleh_chat(client, header_pembaca):
    res = client.post("/chat", json={"session_id": "s", "message": "hai"}, headers=header_pembaca)
    assert res.status_code == 200


def test_readonly_dilarang_tulis_dokumen(client, header_pembaca):
    res = client.post(
        "/documents", json={"filename": "a.txt", "content": "isi"}, headers=header_pembaca
    )
    assert res.status_code == 403
    assert "READ_ONLY" in res.json()["detail"]


def test_user_dilarang_buat_user(client, header_user):
    res = client.post(
        "/auth/users",
        json={"username": "baru", "password": "sandi12345", "role": "USER"},
        headers=header_user,
    )
    assert res.status_code == 403


def test_admin_boleh_buat_user(client, header_admin):
    res = client.post(
        "/auth/users",
        json={"username": "baru", "password": "sandi12345", "role": "USER"},
        headers=header_admin,
    )
    assert res.status_code == 200
    assert res.json()["role"] == "USER"


def test_username_duplikat_ditolak(client, header_admin):
    payload = {"username": "kembar", "password": "sandi12345", "role": "USER"}
    assert client.post("/auth/users", json=payload, headers=header_admin).status_code == 200
    assert client.post("/auth/users", json=payload, headers=header_admin).status_code == 409


def test_role_tidak_dikenal_ditolak(client, header_admin):
    res = client.post(
        "/auth/users",
        json={"username": "x", "password": "sandi12345", "role": "SUPERUSER"},
        headers=header_admin,
    )
    assert res.status_code == 400
