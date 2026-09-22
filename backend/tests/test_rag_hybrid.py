"""Test hybrid retrieval (vector + full-text search dengan RRF)."""

import pytest
from sqlalchemy import text

from config import settings
from database import SessionLocal
from models import Document
from tools.rag_tool import cari_dokumen

DIM = settings.EMBEDDING_DIM


def _simpan(db, filename: str, content: str, vektor: list[float]):
    db.add(Document(filename=filename, content=content, embedding=vektor, metadata_={}))
    db.commit()


@pytest.fixture
def db():
    """Sesi yang dijamin tertutup — sesi menggantung membuat TRUNCATE deadlock."""
    sesi = SessionLocal()
    try:
        yield sesi
    finally:
        sesi.rollback()
        sesi.close()


@pytest.fixture
def korpus(monkeypatch, db):
    """
    Tiga dokumen dengan vektor yang dikendalikan manual.

    Embedding tidak dipanggil ke Ollama; kueri dipetakan ke vektor tetap supaya
    peringkat yang diuji deterministik.
    """
    dekat = [1.0] + [0.0] * (DIM - 1)
    jauh = [0.0] * (DIM - 1) + [1.0]
    tengah = [0.5] * DIM

    _simpan(db, "dekat-vektor.txt", "Panduan umum tanpa istilah khusus.", dekat)
    _simpan(db, "cocok-teks.txt", "Peraturan Bupati Nomor 12 Tahun 2024 tentang tunjangan.", jauh)
    _simpan(db, "netral.txt", "Dokumen lain yang tidak relevan.", tengah)

    monkeypatch.setattr("tools.rag_tool.embed_text", lambda q: dekat)
    yield


def test_kolom_tsvector_terisi_otomatis(db):
    """content_tsv adalah generated column — harus ikut terisi tanpa campur tangan aplikasi."""
    _simpan(db, "a.txt", "Kebijakan retensi dokumen keuangan perusahaan.", [0.1] * DIM)
    isi = db.execute(text("SELECT content_tsv::text FROM documents LIMIT 1")).scalar()
    assert isi
    assert "bijak" in isi   # 'kebijakan' ter-stem oleh konfigurasi indonesian


def test_hybrid_menemukan_istilah_literal_yang_jauh_secara_vektor(korpus, db):
    """
    Dokumen dengan vektor paling jauh tetap terambil karena kata kuncinya cocok.
    Inilah yang tidak bisa dilakukan pencarian vektor sendirian.
    """
    settings.RAG_HYBRID = True
    nama = [h["filename"] for h in cari_dokumen(db, "Peraturan Bupati Nomor 12 Tahun 2024", top_k=3)]
    assert "cocok-teks.txt" in nama


def test_mode_vektor_saja_melewatkan_dokumen_itu(korpus, db):
    settings.RAG_HYBRID = False
    try:
        hasil = cari_dokumen(db, "Peraturan Bupati Nomor 12 Tahun 2024", top_k=1)
        assert hasil[0]["filename"] == "dekat-vektor.txt"
        assert hasil[0]["dari_teks"] is False
    finally:
        settings.RAG_HYBRID = True


def test_asal_hasil_ditandai(korpus, db):
    settings.RAG_HYBRID = True
    hasil = cari_dokumen(db, "Peraturan Bupati Nomor 12 Tahun 2024", top_k=3)
    assert any(h["dari_teks"] for h in hasil)
    assert any(h["dari_vektor"] for h in hasil)


def test_top_k_dihormati(korpus, db):
    settings.RAG_HYBRID = True
    assert len(cari_dokumen(db, "panduan", top_k=2)) <= 2


def test_knowledge_base_kosong_tidak_error(monkeypatch, db):
    monkeypatch.setattr("tools.rag_tool.embed_text", lambda q: [0.1] * DIM)
    assert cari_dokumen(db, "apa saja") == []


# --- pencarian dibatasi pada satu dokumen -----------------------------------

def test_pencarian_dibatasi_pada_dokumen_tertentu(db, monkeypatch):
    """
    Saat user mengunggah berkas lalu bertanya "apa isi dokumennya?", pencarian
    harus dibatasi pada berkas itu. Tanpa pembatasan, potongan dokumen lain
    ikut terambil dan menenggelamkan yang ditanyakan.
    """
    vektor = [0.2] * DIM
    _simpan(db, "diunggah.pdf", "Isi berkas yang baru saja diunggah user.", vektor)
    _simpan(db, "lama-satu.txt", "Dokumen lama pertama.", vektor)
    _simpan(db, "lama-dua.txt", "Dokumen lama kedua.", vektor)
    monkeypatch.setattr("tools.rag_tool.embed_text", lambda q: vektor)

    from tools.rag_tool import cari_dokumen

    semua = {h["filename"] for h in cari_dokumen(db, "isi apa", top_k=5)}
    assert len(semua) > 1, "tanpa pembatasan, dokumen lain memang ikut terambil"

    terbatas = {h["filename"] for h in cari_dokumen(db, "isi apa", top_k=5, filename="diunggah.pdf")}
    assert terbatas == {"diunggah.pdf"}


def test_build_rag_tool_tanpa_filename_mengembalikan_tool_biasa():
    from tools.rag_tool import build_rag_tool, rag_search

    assert build_rag_tool() is rag_search


def test_build_rag_tool_dengan_filename_menjelaskan_cakupannya():
    from tools.rag_tool import build_rag_tool

    t = build_rag_tool("laporan.pdf")
    assert t.name == "rag_search"
    assert "laporan.pdf" in t.description
    assert "apa isi dokumennya" in t.description.lower()


def test_tool_terbatas_membaca_dokumen_yang_dimaksud(db, monkeypatch):
    vektor = [0.3] * DIM
    _simpan(db, "target.pdf", "Pasal 4 menyebut sertifikat berlaku 2 tahun.", vektor)
    _simpan(db, "bukan-target.txt", "Dokumen lain yang tidak relevan.", vektor)
    monkeypatch.setattr("tools.rag_tool.embed_text", lambda q: vektor)

    from tools.rag_tool import build_rag_tool

    hasil = build_rag_tool("target.pdf").invoke({"query": "apa isi dokumennya"})
    assert "sertifikat berlaku 2 tahun" in hasil
    assert "bukan-target.txt" not in hasil
