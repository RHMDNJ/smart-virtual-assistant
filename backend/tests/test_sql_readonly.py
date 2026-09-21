"""
Test bahwa SQL tool berjalan sebagai user database read-only.

Validasi keyword di level aplikasi bisa saja punya celah; privilege database
adalah lapisan yang tidak bisa dinegosiasikan oleh LLM maupun prompt injection.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import SQL_TOOL_READONLY, ReadOnlySessionLocal
from tools.sql_tool import run_readonly_query


def test_koneksi_readonly_aktif():
    assert SQL_TOOL_READONLY, "SQL_READONLY_DATABASE_URL belum diset untuk test."


def test_user_readonly_bukan_pemilik_database():
    db = ReadOnlySessionLocal()
    try:
        assert db.execute(text("SELECT current_user")).scalar() == "sva_readonly"
    finally:
        db.close()


@pytest.mark.parametrize(
    "query",
    [
        "SELECT count(*) FROM users",                 # tabel kredensial
        "SELECT message FROM chat_history LIMIT 1",   # isi percakapan
    ],
)
def test_tabel_sensitif_ditolak_oleh_database(query):
    """Bahkan jika validator aplikasi dilewati, database tetap menolak."""
    db = ReadOnlySessionLocal()
    try:
        with pytest.raises(SQLAlchemyError, match="permission denied"):
            db.execute(text(query))
    finally:
        db.rollback()
        db.close()


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM documents",
        "INSERT INTO documents (filename, content) VALUES ('x', 'y')",
        "UPDATE documents SET content = 'x'",
        "CREATE TABLE nakal (id int)",
    ],
)
def test_penulisan_ditolak_oleh_database(query):
    db = ReadOnlySessionLocal()
    try:
        with pytest.raises(SQLAlchemyError):
            db.execute(text(query))
    finally:
        db.rollback()
        db.close()


def test_query_allowlist_tetap_berjalan():
    hasil = run_readonly_query("SELECT count(*) AS jumlah FROM documents")
    assert hasil[0]["jumlah"] >= 0
