"""Unit test untuk hashing password dan validasi SQL (tanpa HTTP)."""

import pytest

from security import MAX_PASSWORD_BYTES, hash_password, verify_password
from tools.sql_tool import SQLValidationError, validate_query


def test_hash_dan_verifikasi():
    h = hash_password("rahasia123")
    assert h != "rahasia123"
    assert verify_password("rahasia123", h)
    assert not verify_password("rahasia124", h)


def test_hash_berbeda_tiap_kali():
    """Salt acak: dua hash dari password sama tidak boleh identik."""
    assert hash_password("sama") != hash_password("sama")


def test_password_terlalu_panjang_ditolak():
    """bcrypt hanya memakai 72 byte pertama — jangan dipotong diam-diam."""
    with pytest.raises(ValueError):
        hash_password("a" * (MAX_PASSWORD_BYTES + 1))


def test_verifikasi_password_panjang_tidak_meledak():
    h = hash_password("pendek")
    assert not verify_password("a" * 200, h)


# --- SQL tool (SEC-001) -------------------------------------------------------

QUERY_DITOLAK = [
    "DROP TABLE documents",
    "DELETE FROM chat_history",
    "UPDATE documents SET content = 'x'",
    "INSERT INTO documents (filename) VALUES ('x')",
    "TRUNCATE chat_history",
    "SELECT * FROM chat_history; DROP TABLE documents",
    "SELECT * FROM pg_shadow",
    "SELECT * FROM users",           # tabel users tidak di-allowlist
    "SELECT message FROM chat_history",  # tabel mentah: isi percakapan tidak boleh terbaca
    "GRANT ALL ON documents TO public",
]


@pytest.mark.parametrize("query", QUERY_DITOLAK)
def test_query_berbahaya_ditolak(query):
    with pytest.raises(SQLValidationError):
        validate_query(query)


@pytest.mark.parametrize(
    "query",
    [
        "SELECT count(*) FROM chat_stats",
        "select filename from documents limit 5",
        "SELECT role, count(*) FROM chat_stats GROUP BY role;",
    ],
)
def test_query_select_aman_diterima(query):
    validate_query(query)  # tidak boleh melempar exception
