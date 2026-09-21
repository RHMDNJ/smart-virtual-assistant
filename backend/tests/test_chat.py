"""Test endpoint /chat, riwayat, dan validasi image_id."""

from conftest import token_untuk


def test_chat_mengembalikan_kontrak_api(client, header_user):
    res = client.post("/chat", json={"session_id": "s1", "message": "halo"}, headers=header_user)
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"answer", "tool_used", "sources"}
    assert body["answer"].startswith("[stub]")


def test_pesan_kosong_ditolak(client, header_user):
    res = client.post("/chat", json={"session_id": "s1", "message": "   "}, headers=header_user)
    assert res.status_code == 400


def test_riwayat_tersimpan_berpasangan(client, header_user):
    client.post("/chat", json={"session_id": "s1", "message": "pertama"}, headers=header_user)
    riwayat = client.get("/chat/history?session_id=s1", headers=header_user).json()
    assert [r["role"] for r in riwayat] == ["user", "assistant"]
    assert riwayat[0]["message"] == "pertama"


def test_riwayat_terisolasi_antar_user(client, header_user, admin):
    """Session milik user lain tidak boleh bocor meski session_id-nya ditebak."""
    client.post("/chat", json={"session_id": "rahasia", "message": "data sensitif"},
                headers=header_user)

    header_admin = {"Authorization": f"Bearer {token_untuk(client, 'admin_test')}"}
    riwayat_admin = client.get("/chat/history?session_id=rahasia", headers=header_admin).json()
    assert riwayat_admin == []


def test_riwayat_terisolasi_pada_memori_agent(client, header_user, admin, monkeypatch):
    """Memori percakapan yang dikirim ke agent hanya boleh milik user itu sendiri."""
    import main

    client.post("/chat", json={"session_id": "sama", "message": "punya user"}, headers=header_user)

    terekam = {}

    def rekam(message, image_path=None, chat_history=None):
        terekam["history"] = chat_history or []
        return {"answer": "ok", "tool_used": "llm_direct", "sources": []}

    monkeypatch.setattr(main, "run_agent", rekam)

    header_admin = {"Authorization": f"Bearer {token_untuk(client, 'admin_test')}"}
    client.post("/chat", json={"session_id": "sama", "message": "punya admin"}, headers=header_admin)
    assert terekam["history"] == []


def test_memori_percakapan_dikirim_ke_agent(client, header_user, monkeypatch):
    import main

    client.post("/chat", json={"session_id": "m1", "message": "pesan lama"}, headers=header_user)

    terekam = {}

    def rekam(message, image_path=None, chat_history=None):
        terekam["history"] = chat_history or []
        return {"answer": "ok", "tool_used": "llm_direct", "sources": []}

    monkeypatch.setattr(main, "run_agent", rekam)
    client.post("/chat", json={"session_id": "m1", "message": "pesan baru"}, headers=header_user)

    peran = [r for r, _ in terekam["history"]]
    pesan = [m for _, m in terekam["history"]]
    assert peran == ["user", "assistant"]
    assert "pesan lama" in pesan
    assert "pesan baru" not in pesan  # pesan saat ini dikirim lewat `input`, bukan history


# --- validasi image_id (mitigasi path traversal) ------------------------------

def test_image_id_format_salah_ditolak(client, header_user):
    res = client.post(
        "/chat",
        json={"session_id": "s", "message": "baca", "image_id": "bukan-uuid.png"},
        headers=header_user,
    )
    assert res.status_code == 400


def test_image_id_path_traversal_ditolak(client, header_user):
    res = client.post(
        "/chat",
        json={"session_id": "s", "message": "baca", "image_id": "../../../../etc/passwd"},
        headers=header_user,
    )
    assert res.status_code == 400


def test_image_id_valid_tapi_tidak_ada_file(client, header_user):
    res = client.post(
        "/chat",
        json={"session_id": "s", "message": "baca", "image_id": "a" * 32 + ".png"},
        headers=header_user,
    )
    assert res.status_code == 404
