"""
file_validation.py
Validasi berkas unggahan (Bagian 18 — File Upload Security):
ekstensi, MIME type, file signature (magic bytes), dan ukuran.

Ekstensi dan MIME type keduanya dikirim oleh client, jadi keduanya bisa dipalsukan.
Pertahanan sebenarnya ada pada file signature: isi berkas harus cocok dengan
jenis yang diklaim.
"""

import os
from dataclasses import dataclass

ALLOWED_DOCUMENT_EXT = {".pdf", ".txt", ".md"}
ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_EXT = ALLOWED_DOCUMENT_EXT | ALLOWED_IMAGE_EXT

# MIME type yang wajar untuk tiap ekstensi. Browser kadang mengirim
# application/octet-stream, jadi nilai itu diterima dan keputusan diserahkan
# ke pemeriksaan signature.
MIME_WAJAR = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain", "text/markdown"},
    ".md": {"text/markdown", "text/plain", "text/x-markdown"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
}
MIME_NETRAL = {"application/octet-stream", ""}

# Byte pembuka yang menandai jenis berkas sebenarnya.
SIGNATURE = {
    ".pdf": [b"%PDF-"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
}

BYTE_HEADER = 64


class FileValidationError(Exception):
    """Berkas ditolak. Pesannya aman untuk ditampilkan ke user."""


@dataclass
class HasilValidasi:
    ext: str
    adalah_dokumen: bool


def validasi_ekstensi(filename: str | None) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise FileValidationError(f"Tipe file tidak didukung: {ext or '(tanpa ekstensi)'}")
    return ext


def validasi_mime(ext: str, content_type: str | None) -> None:
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime in MIME_NETRAL:
        return
    if mime not in MIME_WAJAR[ext]:
        raise FileValidationError(
            f"MIME type '{mime}' tidak cocok dengan ekstensi '{ext}'."
        )


def validasi_signature(ext: str, header: bytes) -> None:
    """Cocokkan isi berkas dengan jenis yang diklaim ekstensinya."""
    if ext == ".webp":
        # RIFF....WEBP — 4 byte ukuran berada di antaranya.
        if not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
            raise FileValidationError("Isi berkas bukan gambar WEBP yang valid.")
        return

    if ext in (".txt", ".md"):
        # Teks tidak punya magic bytes; tolak yang mengandung byte NUL atau
        # bukan UTF-8 (indikasi berkas biner yang disamarkan).
        if b"\x00" in header:
            raise FileValidationError("Berkas teks mengandung byte biner.")
        try:
            header.decode("utf-8")
        except UnicodeDecodeError:
            # Potongan header bisa memotong karakter multibyte di tengah;
            # yang penting tidak ada byte kontrol biner.
            if any(b < 9 or 13 < b < 32 for b in header):
                raise FileValidationError("Berkas teks mengandung byte biner.") from None
        return

    pola = SIGNATURE[ext]
    if not any(header.startswith(p) for p in pola):
        raise FileValidationError(
            f"Isi berkas tidak cocok dengan ekstensi '{ext}' (file signature salah)."
        )


def simpan_dengan_batas(sumber, tujuan_path: str, maks_byte: int) -> int:
    """
    Salin stream ke disk sambil menegakkan batas ukuran.

    Batas dicek selama penyalinan, bukan sesudahnya, supaya unggahan raksasa
    tidak sempat memenuhi disk lebih dulu.
    """
    total = 0
    try:
        with open(tujuan_path, "wb") as keluaran:
            while True:
                potongan = sumber.read(1024 * 1024)
                if not potongan:
                    break
                total += len(potongan)
                if total > maks_byte:
                    raise FileValidationError("Ukuran file melebihi batas maksimum.")
                keluaran.write(potongan)
    except FileValidationError:
        if os.path.exists(tujuan_path):
            os.remove(tujuan_path)
        raise
    return total


def validasi_unggahan(filename: str | None, content_type: str | None, header: bytes) -> HasilValidasi:
    ext = validasi_ekstensi(filename)
    validasi_mime(ext, content_type)
    validasi_signature(ext, header)
    return HasilValidasi(ext=ext, adalah_dokumen=ext in ALLOWED_DOCUMENT_EXT)
