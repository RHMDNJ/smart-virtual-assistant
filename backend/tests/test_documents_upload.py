"""Test indexing dokumen, upload file, dan validasinya."""

import io

from sqlalchemy import select

from config import settings
from database import SessionLocal
from models import Document


def test_documents_mengindeks_teks(client, header_user):
    res = client.post(
        "/documents",
        json={"filename": "kebijakan.txt", "content": "Cuti tahunan 14 hari kerja per tahun."},
        headers=header_user,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "indexed"
    assert body["chunks"] >= 1

    db = SessionLocal()
    try:
        docs = list(db.execute(select(Document)).scalars())
        assert len(docs) == body["chunks"]
        assert docs[0].filename == "kebijakan.txt"
        assert docs[0].metadata_ == {"source": "kebijakan.txt"}
        assert len(docs[0].embedding) == settings.EMBEDDING_DIM
    finally:
        db.close()


def test_documents_konten_kosong_ditolak(client, header_user):
    res = client.post(
        "/documents", json={"filename": "a.txt", "content": "   "}, headers=header_user
    )
    assert res.status_code == 400


def test_upload_txt_terindeks(client, header_user):
    berkas = {"file": ("catatan.txt", io.BytesIO(b"Jam kerja 08.00 sampai 17.00 WITA."), "text/plain")}
    res = client.post("/upload", files=berkas, headers=header_user)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "processed"
    assert body["image_id"] is None


def test_upload_gambar_mengembalikan_image_id(client, header_user):
    # PNG 1x1 minimal
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    )
    berkas = {"file": ("struk.png", io.BytesIO(png), "image/png")}
    res = client.post("/upload", files=berkas, headers=header_user)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "uploaded"
    assert body["image_id"].endswith(".png")
    assert len(body["image_id"]) == 36  # 32 hex + ".png"


def test_upload_ekstensi_tidak_didukung_ditolak(client, header_user):
    berkas = {"file": ("jahat.exe", io.BytesIO(b"MZ"), "application/octet-stream")}
    res = client.post("/upload", files=berkas, headers=header_user)
    assert res.status_code == 400
    assert "tidak didukung" in res.json()["detail"]


def test_upload_ditolak_untuk_readonly(client, header_pembaca):
    berkas = {"file": ("catatan.txt", io.BytesIO(b"isi"), "text/plain")}
    res = client.post("/upload", files=berkas, headers=header_pembaca)
    assert res.status_code == 403
