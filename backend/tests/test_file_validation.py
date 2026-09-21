"""Test validasi unggahan: ekstensi, MIME, file signature, dan batas ukuran."""

import io

import pytest

from file_validation import FileValidationError, validasi_unggahan

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 40
PDF = b"%PDF-1.7\n" + b"x" * 40
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"x" * 40
ELF = b"\x7fELF" + b"\x00" * 40


# --- unit --------------------------------------------------------------------

@pytest.mark.parametrize(
    "nama,mime,isi",
    [
        ("a.png", "image/png", PNG),
        ("a.jpg", "image/jpeg", JPEG),
        ("a.pdf", "application/pdf", PDF),
        ("a.webp", "image/webp", WEBP),
        ("a.txt", "text/plain", b"halo dunia"),
        ("a.md", "text/markdown", b"# Judul"),
        ("a.png", "application/octet-stream", PNG),  # MIME netral tetap diterima
    ],
)
def test_berkas_sah_diterima(nama, mime, isi):
    validasi_unggahan(nama, mime, isi)


def test_ekstensi_tidak_didukung():
    with pytest.raises(FileValidationError, match="tidak didukung"):
        validasi_unggahan("virus.exe", "application/octet-stream", b"MZ")


def test_tanpa_ekstensi():
    with pytest.raises(FileValidationError):
        validasi_unggahan("berkas", "text/plain", b"halo")


def test_mime_bertentangan_dengan_ekstensi():
    with pytest.raises(FileValidationError, match="MIME type"):
        validasi_unggahan("a.png", "application/pdf", PNG)


def test_biner_menyamar_sebagai_png():
    """Ekstensi dan MIME benar, tapi isinya ELF — harus ditolak oleh signature."""
    with pytest.raises(FileValidationError, match="file signature"):
        validasi_unggahan("jahat.png", "image/png", ELF)


def test_biner_menyamar_sebagai_txt():
    with pytest.raises(FileValidationError, match="biner"):
        validasi_unggahan("jahat.txt", "text/plain", ELF)


def test_pdf_palsu_ditolak():
    with pytest.raises(FileValidationError, match="file signature"):
        validasi_unggahan("palsu.pdf", "application/pdf", b"ini bukan pdf sama sekali")


def test_webp_tanpa_penanda_ditolak():
    with pytest.raises(FileValidationError, match="WEBP"):
        validasi_unggahan("a.webp", "image/webp", b"RIFF" + b"\x00" * 20)


# --- lewat endpoint ----------------------------------------------------------

def test_upload_menolak_biner_menyamar(client, header_user):
    berkas = {"file": ("jahat.png", io.BytesIO(ELF), "image/png")}
    res = client.post("/upload", files=berkas, headers=header_user)
    assert res.status_code == 400
    assert "signature" in res.json()["detail"]


def test_upload_menolak_mime_tidak_cocok(client, header_user):
    berkas = {"file": ("a.png", io.BytesIO(PNG), "application/pdf")}
    res = client.post("/upload", files=berkas, headers=header_user)
    assert res.status_code == 400


def test_upload_menolak_file_kebesaran_tanpa_menyisakan_sampah(client, header_user, monkeypatch):
    import os

    from config import settings

    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    besar = PNG + b"\x00" * (2 * 1024 * 1024)
    berkas = {"file": ("besar.png", io.BytesIO(besar), "image/png")}

    sebelum = set(os.listdir(settings.UPLOAD_DIR))
    res = client.post("/upload", files=berkas, headers=header_user)
    sesudah = set(os.listdir(settings.UPLOAD_DIR))

    assert res.status_code == 400
    assert "melebihi batas" in res.json()["detail"]
    assert sebelum == sesudah, "berkas gagal harus dibersihkan dari disk"


def test_upload_png_sah_berhasil(client, header_user):
    berkas = {"file": ("struk.png", io.BytesIO(PNG), "image/png")}
    res = client.post("/upload", files=berkas, headers=header_user)
    assert res.status_code == 200
    assert res.json()["image_id"].endswith(".png")
