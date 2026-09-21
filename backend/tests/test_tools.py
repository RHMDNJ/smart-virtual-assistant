"""Test perilaku tool di luar jalur HTTP."""

from tools.ocr_tool import image_ocr
from tools.rag_tool import rag_search
from tools.sql_tool import build_sql_tool, describe_allowed_schema


def test_rag_query_kosong_tidak_memanggil_embedding(monkeypatch):
    """Guard query kosong harus berhenti sebelum menyentuh embedding/DB."""
    dipanggil = {"embed": False}

    def jangan_dipanggil(_):
        dipanggil["embed"] = True
        raise AssertionError("embed_text seharusnya tidak dipanggil")

    monkeypatch.setattr("tools.rag_tool.embed_text", jangan_dipanggil)

    hasil = rag_search.invoke({"query": "   "})
    assert "Query kosong" in hasil
    assert dipanggil["embed"] is False


def test_ocr_menangani_file_hilang_tanpa_crash():
    """Kegagalan OCR harus jadi pesan, bukan exception yang menjatuhkan agent."""
    hasil = image_ocr.invoke({"image_path": "/tmp/tidak-ada-file-ini.png"})
    assert "Gagal membaca gambar" in hasil or "Tidak ada teks" in hasil


def test_deskripsi_sql_tool_memuat_skema_nyata():
    """Tanpa skema di deskripsi, agent mengarang kolom yang tidak ada."""
    deskripsi = build_sql_tool().description
    assert "chat_stats(" in deskripsi
    assert "documents(" in deskripsi
    assert "session_id" in deskripsi


def test_skema_tidak_membocorkan_tabel_sensitif():
    deskripsi = describe_allowed_schema()
    assert "users(" not in deskripsi          # kredensial tidak boleh diekspos
    assert "password_hash" not in deskripsi
    assert "chat_history(" not in deskripsi   # tabel mentah diganti view chat_stats


def test_isi_percakapan_tidak_dapat_dibaca_lewat_sql():
    """
    Regresi: sebelum ada view chat_stats, agent bisa menjalankan
    `SELECT message FROM chat_history` dan membaca percakapan user lain.
    """
    from tools.sql_tool import SQLValidationError, validate_query

    for query in (
        "SELECT message FROM chat_history",
        "SELECT user_id, message FROM chat_history WHERE user_id = 1",
    ):
        try:
            validate_query(query)
        except SQLValidationError:
            continue
        raise AssertionError(f"Query seharusnya ditolak: {query}")

    # Kolom message memang tidak ada pada view yang diizinkan.
    assert "message" not in describe_allowed_schema().split("documents(")[0]
