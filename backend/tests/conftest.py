"""
conftest.py
Fixture bersama untuk test suite.

Dua keputusan penting:
1. Test memakai database terpisah (`agentic_rag_test`) supaya data development
   tidak ikut terhapus. DATABASE_URL disetel SEBELUM `config` diimport.
2. LLM (Ollama) dan embedding di-mock. Test di sini menguji API, auth, dan
   validasi — bukan kualitas jawaban model, yang tidak deterministik dan lambat.
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:mysecretpassword@localhost:5432/agentic_rag_test"
)
os.environ.setdefault(
    "SQL_READONLY_DATABASE_URL",
    "postgresql://sva_readonly:readonly_secret@localhost:5432/agentic_rag_test",
)
os.environ.setdefault("APP_ENV", "development")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import main  # noqa: E402
from config import settings  # noqa: E402
from database import SessionLocal, engine, init_db  # noqa: E402
from models import User  # noqa: E402
from security import ROLE_ADMIN, ROLE_READ_ONLY, ROLE_USER, hash_password  # noqa: E402

EMBEDDING_DUMMY = [0.01] * settings.EMBEDDING_DIM


@pytest.fixture(scope="session", autouse=True)
def siapkan_database():
    assert "test" in settings.DATABASE_URL, "Test menolak jalan di database non-test."
    init_db()

    # init_db sengaja tidak mengubah dimensi kolom embedding secara otomatis
    # (di produksi itu berarti membuang data). Di database test datanya memang
    # sekali pakai, jadi kolomnya dibuat ulang bila dimensinya berbeda.
    from reindex_embeddings import buat_ulang_kolom, dimensi_kolom_sekarang

    with engine.connect() as conn:
        if dimensi_kolom_sekarang(conn) != settings.EMBEDDING_DIM:
            perlu = True
        else:
            perlu = False
    if perlu:
        buat_ulang_kolom(settings.EMBEDDING_DIM)

    yield


@pytest.fixture(autouse=True)
def bersihkan_tabel():
    """Setiap test mulai dari database kosong agar tidak saling mempengaruhi."""
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE chat_history, documents, users RESTART IDENTITY CASCADE;"))
        conn.commit()
    yield


@pytest.fixture(autouse=True)
def matikan_llm_dan_embedding(monkeypatch):
    """Ganti pemanggilan Ollama dengan stub deterministik."""

    def fake_run_agent(message, image_path=None, chat_history=None):
        return {
            "answer": f"[stub] {message}",
            "tool_used": "image_ocr" if image_path else "llm_direct",
            "sources": [],
        }

    async def fake_run_agent_stream(message, image_path=None, chat_history=None):
        yield {"type": "tool", "name": "rag_search"}
        for potongan in ("Ini ", "jawaban ", "bertahap."):
            yield {"type": "token", "text": potongan}
        yield {
            "type": "done",
            "answer": "Ini jawaban bertahap.",
            "tool_used": "rag_search",
            "sources": [{"filename": "kebijakan.txt"}],
        }

    monkeypatch.setattr(main, "run_agent", fake_run_agent)
    monkeypatch.setattr(main, "run_agent_stream", fake_run_agent_stream)
    monkeypatch.setattr(
        "services.document_service.embed_documents",
        lambda texts: [EMBEDDING_DUMMY for _ in texts],
    )


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


def _buat_user(username: str, password: str, role: str) -> User:
    db = SessionLocal()
    try:
        user = User(username=username, password_hash=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture
def admin():
    return _buat_user("admin_test", "sandi12345", ROLE_ADMIN)


@pytest.fixture
def user_biasa():
    return _buat_user("user_test", "sandi12345", ROLE_USER)


@pytest.fixture
def pembaca():
    return _buat_user("pembaca_test", "sandi12345", ROLE_READ_ONLY)


def token_untuk(client: TestClient, username: str, password: str = "sandi12345") -> str:
    res = client.post("/auth/login", data={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture
def header_admin(client, admin):
    return {"Authorization": f"Bearer {token_untuk(client, admin.username)}"}


@pytest.fixture
def header_user(client, user_biasa):
    return {"Authorization": f"Bearer {token_untuk(client, user_biasa.username)}"}


@pytest.fixture
def header_pembaca(client, pembaca):
    return {"Authorization": f"Bearer {token_untuk(client, pembaca.username)}"}
