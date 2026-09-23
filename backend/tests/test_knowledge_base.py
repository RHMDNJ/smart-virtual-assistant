"""Test pengelolaan knowledge base (fitur 'melatih' SAVIRA)."""

import io

import pytest


def buat(client, headers, filename="a.txt", content="Isi dokumen pertama."):
    return client.post("/documents", json={"filename": filename, "content": content}, headers=headers)


# --- daftar & detail ---------------------------------------------------------

def test_daftar_kosong(client, header_user):
    assert client.get("/documents", headers=header_user).json() == []


def test_daftar_meringkas_per_dokumen(client, header_user):
    buat(client, header_user, "satu.txt", "Dokumen satu.")
    buat(client, header_user, "dua.txt", "Dokumen dua yang lebih panjang sedikit.")

    daftar = client.get("/documents", headers=header_user).json()
    nama = [d["filename"] for d in daftar]
    assert nama == ["dua.txt", "satu.txt"]          # urut menurut nama
    assert all(d["chunks"] >= 1 for d in daftar)
    assert all(d["characters"] > 0 for d in daftar)


def test_detail_menggabungkan_chunk(client, header_user):
    panjang = "Kalimat pembuka. " * 200              # cukup panjang untuk dipecah
    buat(client, header_user, "panjang.txt", panjang)

    d = client.get("/documents/panjang.txt", headers=header_user).json()
    assert d["chunks"] > 1, "teks panjang seharusnya terpecah"
    assert "Kalimat pembuka." in d["content"]


def test_detail_dokumen_tidak_ada(client, header_user):
    assert client.get("/documents/hantu.txt", headers=header_user).status_code == 404


def test_readonly_boleh_melihat(client, header_user, header_pembaca):
    buat(client, header_user, "publik.txt", "Isi yang boleh dibaca.")
    assert client.get("/documents", headers=header_pembaca).status_code == 200
    assert client.get("/documents/publik.txt", headers=header_pembaca).status_code == 200


# --- membuat & memperbarui ---------------------------------------------------

def test_nama_duplikat_ditolak(client, header_user):
    assert buat(client, header_user).status_code == 200
    res = buat(client, header_user)
    assert res.status_code == 409
    assert "PUT" in res.json()["detail"]


def test_update_mengganti_isi_bukan_menambah(client, header_user):
    buat(client, header_user, "ganti.txt", "Versi pertama.")
    client.put("/documents/ganti.txt", json={"content": "Versi kedua."}, headers=header_user)

    d = client.get("/documents/ganti.txt", headers=header_user).json()
    assert "Versi kedua." in d["content"]
    assert "Versi pertama." not in d["content"], "chunk lama harus dibuang, bukan ditumpuk"
    assert len(client.get("/documents", headers=header_user).json()) == 1


def test_update_dokumen_tidak_ada(client, header_user):
    res = client.put("/documents/hantu.txt", json={"content": "x"}, headers=header_user)
    assert res.status_code == 404


def test_update_konten_kosong_ditolak(client, header_user):
    buat(client, header_user, "b.txt")
    res = client.put("/documents/b.txt", json={"content": "   "}, headers=header_user)
    assert res.status_code == 400


def test_readonly_tidak_boleh_menulis(client, header_user, header_pembaca):
    buat(client, header_user, "c.txt")
    assert client.put("/documents/c.txt", json={"content": "x"}, headers=header_pembaca).status_code == 403
    assert client.post("/documents", json={"filename": "d.txt", "content": "x"}, headers=header_pembaca).status_code == 403


# --- menghapus ---------------------------------------------------------------

def test_hapus_hanya_admin(client, header_user, header_admin):
    buat(client, header_user, "hapus.txt")
    assert client.delete("/documents/hapus.txt", headers=header_user).status_code == 403
    assert client.delete("/documents/hapus.txt", headers=header_admin).status_code == 200
    assert client.get("/documents/hapus.txt", headers=header_admin).status_code == 404


def test_hapus_membuang_semua_chunk(client, header_user, header_admin):
    buat(client, header_user, "besar.txt", "Kalimat panjang. " * 200)
    jumlah = client.get("/documents/besar.txt", headers=header_admin).json()["chunks"]
    assert jumlah > 1

    hasil = client.delete("/documents/besar.txt", headers=header_admin).json()
    assert hasil["chunks"] == jumlah
    assert client.get("/documents", headers=header_admin).json() == []


def test_hapus_dokumen_tidak_ada(client, header_admin):
    assert client.delete("/documents/hantu.txt", headers=header_admin).status_code == 404


# --- indeks ulang ------------------------------------------------------------

def test_reindex_hanya_admin(client, header_user, header_admin):
    buat(client, header_user, "r.txt", "Isi untuk diindeks ulang.")
    assert client.post("/documents/reindex", headers=header_user).status_code == 403
    assert client.post("/documents/reindex", headers=header_admin).status_code == 200


def test_reindex_bawaan_melewati_yang_sudah_terindeks(client, header_user, header_admin):
    """
    Dokumen yang sudah punya embedding tidak boleh dihitung ulang percuma —
    menghitung ulang seluruh knowledge base memakan waktu lama.
    """
    buat(client, header_user, "sudah.txt", "Sudah terindeks saat diunggah.")

    hasil = client.post("/documents/reindex", headers=header_admin).json()
    assert hasil["reindexed"] == 0
    assert hasil["skipped"] == hasil["total"] >= 1


def test_reindex_semua_memproses_seluruhnya(client, header_user, header_admin):
    """Paksa semua hanya perlu setelah embedding model diganti."""
    buat(client, header_user, "a.txt", "Dokumen pertama.")
    buat(client, header_user, "b.txt", "Dokumen kedua.")

    hasil = client.post("/documents/reindex?semua=true", headers=header_admin).json()
    assert hasil["reindexed"] == hasil["total"] >= 2
    assert hasil["skipped"] == 0


def test_reindex_mengisi_embedding_yang_kosong(client, header_user, header_admin):
    """Bagian yang embedding-nya hilang harus terisi oleh mode bawaan."""
    from sqlalchemy import update

    from database import SessionLocal
    from models import Document

    buat(client, header_user, "bolong.txt", "Embedding-nya akan dikosongkan.")

    db = SessionLocal()
    try:
        db.execute(update(Document).values(embedding=None))
        db.commit()
    finally:
        db.close()

    hasil = client.post("/documents/reindex", headers=header_admin).json()
    assert hasil["reindexed"] >= 1
    assert hasil["skipped"] == 0


def test_reindex_tanpa_dokumen(client, header_admin):
    hasil = client.post("/documents/reindex", headers=header_admin).json()
    assert hasil == {"reindexed": 0, "skipped": 0, "total": 0}


# --- unggah berkas -----------------------------------------------------------

def test_unggah_nama_sama_mengganti_bukan_menduplikasi(client, header_user):
    """Mengunggah ulang berkas yang sama berarti memperbarui isinya."""
    berkas1 = {"file": ("catatan.txt", io.BytesIO(b"Versi pertama berkas."), "text/plain")}
    berkas2 = {"file": ("catatan.txt", io.BytesIO(b"Versi kedua berkas."), "text/plain")}

    client.post("/upload", files=berkas1, headers=header_user)
    res = client.post("/upload", files=berkas2, headers=header_user)

    assert "menggantikan" in res.json()["detail"]
    daftar = client.get("/documents", headers=header_user).json()
    assert len(daftar) == 1

    isi = client.get("/documents/catatan.txt", headers=header_user).json()["content"]
    assert "Versi kedua" in isi and "Versi pertama" not in isi


@pytest.mark.parametrize("path", ["/documents", "/documents/a.txt"])
def test_butuh_autentikasi(client, path):
    assert client.get(path).status_code == 401
