"""Test endpoint /chat/stream (Server-Sent Events)."""

import json

from sqlalchemy import select

from database import SessionLocal
from models import ChatHistory


def baca_event(res) -> list[dict]:
    peristiwa = []
    for blok in res.text.split("\n\n"):
        for baris in blok.split("\n"):
            if baris.startswith("data: "):
                peristiwa.append(json.loads(baris[6:]))
    return peristiwa


def test_stream_butuh_autentikasi(client):
    res = client.post("/chat/stream", json={"session_id": "s", "message": "hai"})
    assert res.status_code == 401


def test_stream_mengembalikan_content_type_sse(client, header_user):
    res = client.post("/chat/stream", json={"session_id": "s", "message": "hai"}, headers=header_user)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    assert res.headers.get("cache-control") == "no-cache"


def test_urutan_event(client, header_user):
    res = client.post("/chat/stream", json={"session_id": "s", "message": "hai"}, headers=header_user)
    peristiwa = baca_event(res)

    jenis = [e["type"] for e in peristiwa]
    assert jenis[0] == "tool"
    assert jenis[-1] == "done"
    assert jenis.count("token") == 3

    selesai = peristiwa[-1]
    assert selesai["answer"] == "Ini jawaban bertahap."
    assert selesai["tool_used"] == "rag_search"
    assert selesai["sources"] == [{"filename": "kebijakan.txt"}]


def test_token_jika_digabung_sama_dengan_jawaban(client, header_user):
    peristiwa = baca_event(
        client.post("/chat/stream", json={"session_id": "s", "message": "hai"}, headers=header_user)
    )
    gabungan = "".join(e["text"] for e in peristiwa if e["type"] == "token")
    assert gabungan == peristiwa[-1]["answer"]


def test_pesan_kosong_ditolak_sebelum_stream(client, header_user):
    res = client.post("/chat/stream", json={"session_id": "s", "message": "  "}, headers=header_user)
    assert res.status_code == 400


def test_image_id_tidak_valid_ditolak_sebelum_stream(client, header_user):
    res = client.post(
        "/chat/stream",
        json={"session_id": "s", "message": "baca", "image_id": "../../etc/passwd"},
        headers=header_user,
    )
    assert res.status_code == 400


def test_riwayat_tersimpan_setelah_stream_selesai(client, header_user):
    client.post("/chat/stream", json={"session_id": "sx", "message": "tanya"}, headers=header_user)

    db = SessionLocal()
    try:
        baris = list(
            db.execute(
                select(ChatHistory).where(ChatHistory.session_id == "sx").order_by(ChatHistory.id)
            ).scalars()
        )
    finally:
        db.close()

    assert [b.role for b in baris] == ["user", "assistant"]
    assert baris[1].message == "Ini jawaban bertahap."


def test_kegagalan_di_tengah_stream_jadi_event_error(client, header_user, monkeypatch):
    """Header sudah terkirim, jadi error tidak bisa lagi jadi HTTP 500."""
    import main

    async def gagal(message, image_path=None, chat_history=None):
        yield {"type": "token", "text": "mulai"}
        raise RuntimeError("ollama mati")

    monkeypatch.setattr(main, "run_agent_stream", gagal)

    res = client.post("/chat/stream", json={"session_id": "s", "message": "hai"}, headers=header_user)
    peristiwa = baca_event(res)

    assert res.status_code == 200
    assert peristiwa[-1]["type"] == "error"
    assert "ollama mati" in peristiwa[-1]["detail"]


def test_readonly_boleh_streaming(client, header_pembaca):
    res = client.post("/chat/stream", json={"session_id": "s", "message": "hai"}, headers=header_pembaca)
    assert res.status_code == 200
