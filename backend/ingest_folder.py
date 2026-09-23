"""
ingest_folder.py
Indeks seluruh dokumen dalam satu folder ke knowledge base SAVIRA.

Dipakai untuk memasukkan bahan resmi dalam jumlah banyak: Perda, Perbup, SOP,
profil daerah, atau halaman situs yang Anda simpan sendiri dari browser.

    .venv/bin/python ingest_folder.py ~/Documents/bahan-savira
    .venv/bin/python ingest_folder.py ~/bahan --replace      # timpa yang sudah ada
    .venv/bin/python ingest_folder.py ~/bahan --dry-run      # lihat dulu, tanpa mengubah

Format yang didukung: .pdf (termasuk hasil pindai, lewat OCR), .txt, .md, .html.
Berkas yang sudah ada di knowledge base dilewati kecuali --replace diberikan.
"""

import argparse
import os
import sys
import time

from database import SessionLocal
from services.document_service import (
    _load_raw_text,
    dokumen_ada,
    ganti_dokumen,
    index_text,
)

EKSTENSI = {".pdf", ".txt", ".md", ".html", ".htm"}


def teks_dari_html(path: str) -> str:
    """Ambil teks yang terbaca manusia dari halaman HTML yang disimpan."""
    from bs4 import BeautifulSoup

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        sup = BeautifulSoup(f.read(), "html.parser")

    # Navigasi, skrip, dan gaya bukan isi dokumen — membuangnya mencegah menu
    # situs ikut terindeks dan mengotori hasil pencarian.
    for tag in sup(["script", "style", "nav", "header", "footer", "form", "noscript"]):
        tag.decompose()

    baris = [b.strip() for b in sup.get_text("\n").splitlines()]
    return "\n".join(b for b in baris if b)


def baca(path: str) -> str:
    if os.path.splitext(path)[1].lower() in (".html", ".htm"):
        return teks_dari_html(path)
    return _load_raw_text(path)


def main() -> int:
    p = argparse.ArgumentParser(description="Indeks folder berisi dokumen ke knowledge base.")
    p.add_argument("folder")
    p.add_argument("--replace", action="store_true", help="Timpa dokumen yang namanya sudah ada.")
    p.add_argument("--dry-run", action="store_true", help="Tampilkan rencana tanpa mengubah apa pun.")
    a = p.parse_args()

    if not os.path.isdir(a.folder):
        print(f"Folder tidak ditemukan: {a.folder}", file=sys.stderr)
        return 1

    berkas = []
    for akar, _, nama_nama in os.walk(a.folder):
        for nama in sorted(nama_nama):
            if nama.startswith("."):
                continue
            if os.path.splitext(nama)[1].lower() in EKSTENSI:
                berkas.append(os.path.join(akar, nama))

    if not berkas:
        print(f"Tidak ada berkas yang didukung di {a.folder} ({', '.join(sorted(EKSTENSI))}).")
        return 0

    print(f"{len(berkas)} berkas ditemukan.\n")
    db = SessionLocal()
    diindeks = dilewati = gagal = 0
    try:
        for i, path in enumerate(berkas, 1):
            nama = os.path.basename(path)
            ada = dokumen_ada(db, nama)

            if ada and not a.replace:
                print(f"  [{i}/{len(berkas)}] lewati   {nama[:58]}  (sudah ada)")
                dilewati += 1
                continue

            if a.dry_run:
                print(f"  [{i}/{len(berkas)}] {'timpa' if ada else 'baru '}    {nama[:58]}")
                continue

            t0 = time.time()
            try:
                teks = baca(path)
                if not teks.strip():
                    raise ValueError("tidak ada teks yang dapat diekstrak")
                jumlah = (
                    ganti_dokumen(db, nama, teks) if ada else index_text(db, teks, nama)
                )
            except Exception as exc:  # noqa: BLE001
                # Satu berkas bermasalah tidak boleh menghentikan sisanya.
                db.rollback()
                print(f"  [{i}/{len(berkas)}] GAGAL    {nama[:58]}  ({exc})")
                gagal += 1
                continue

            print(
                f"  [{i}/{len(berkas)}] {'diganti' if ada else 'diindeks'} {nama[:58]}"
                f"  {jumlah} bagian, {time.time()-t0:.1f}s"
            )
            diindeks += 1
    finally:
        db.close()

    print(f"\nSelesai: {diindeks} diindeks, {dilewati} dilewati, {gagal} gagal.")
    if a.dry_run:
        print("(dry-run — tidak ada yang diubah)")
    return 1 if gagal else 0


if __name__ == "__main__":
    raise SystemExit(main())
