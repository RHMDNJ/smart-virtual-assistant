"""
document_service.py
Pipeline RAG untuk indexing dokumen (Bagian 9 di README):
Document -> Loader -> Cleaning -> Chunking -> Embedding -> pgvector
"""

import logging
import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from config import settings
from models import Document
from services.embedding_service import embed_documents

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)


# Karakter yang lazim pada dokumen berbahasa Indonesia. Teks yang sebagian besar
# di luar himpunan ini hampir pasti hasil ekstraksi yang gagal.
_KARAKTER_WAJAR = set(".,;:()[]{}/-–—%&'\"?!+*=#@<>|~`$^_\\")


def _teks_kacau(teks: str, ambang: float = 0.7) -> bool:
    """
    True bila teks tampak hasil ekstraksi yang gagal.

    Sebagian PDF memakai font subset tanpa peta ToUnicode, sehingga pypdf
    mengembalikan simbol seperti 'ʽ˔˞˔˥˧˔' alih-alih huruf. Teks semacam itu
    lolos pemeriksaan "tidak kosong" tetapi tidak bermakna bagi embedding
    maupun bagi model — halaman itu perlu di-OCR seperti halaman pindaian.
    """
    bersih = [c for c in teks if not c.isspace()]
    if len(bersih) < 20:
        return False
    wajar = sum(1 for c in bersih if c.isascii() and (c.isalnum() or c in _KARAKTER_WAJAR))
    return (wajar / len(bersih)) < ambang


def _ocr_halaman_pdf(file_path: str, halaman_kosong: set[int]) -> dict[int, str]:
    """
    Render halaman PDF yang tidak punya teks, lalu baca dengan OCR.

    PDF hasil pindai hanyalah gambar yang dibungkus PDF — tanpa langkah ini
    dokumen semacam itu ditolak dengan pesan "tidak memiliki konten teks",
    padahal isinya terbaca jelas oleh mata.
    """
    import pymupdf

    from tools.ocr_tool import extract_text_from_image

    hasil: dict[int, str] = {}
    zoom = settings.OCR_PDF_DPI / 72  # PDF memakai 72 dpi sebagai basis
    berkas = pymupdf.open(file_path)
    try:
        for nomor in sorted(halaman_kosong)[: settings.OCR_PDF_MAX_PAGES]:
            gambar = berkas[nomor].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            sementara = f"{file_path}.hal{nomor}.png"
            gambar.save(sementara)
            try:
                teks = extract_text_from_image(sementara)
                if teks.strip():
                    hasil[nomor] = teks
            except Exception:  # noqa: BLE001
                # Satu halaman bermasalah tidak boleh membuang halaman lain
                # pada dokumen pindaian yang tebal.
                logging.getLogger(__name__).warning(
                    "OCR gagal pada halaman %s dari %s; halaman dilewati.", nomor + 1, file_path,
                    exc_info=True,
                )
            finally:
                if os.path.exists(sementara):
                    os.remove(sementara)
    finally:
        berkas.close()
    return hasil


def _load_raw_text(file_path: str) -> str:
    """Load teks mentah dari file PDF/TXT. Untuk gambar, gunakan ocr_tool terlebih dahulu."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        isi = [p.page_content for p in pages]

        # Halaman tanpa teks berarti hasil pindai; hanya halaman itu yang di-OCR,
        # sehingga PDF campuran (sebagian teks, sebagian pindaian) tetap utuh.
        # Halaman yang teksnya kacau (font subset tanpa peta Unicode) juga perlu
        # di-OCR: isinya ada, tetapi tidak terbaca oleh embedding maupun model.
        kosong = {
            i for i, teks in enumerate(isi) if not teks.strip() or _teks_kacau(teks)
        }
        if kosong and settings.OCR_PDF_FALLBACK:
            for nomor, teks in _ocr_halaman_pdf(file_path, kosong).items():
                if nomor < len(isi):
                    isi[nomor] = teks

        return "\n\n".join(t for t in isi if t.strip())

    if ext in (".txt", ".md"):
        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
        return "\n\n".join(d.page_content for d in docs)

    raise ValueError(f"Tipe file tidak didukung untuk indexing dokumen: {ext}")


def index_text(db: Session, raw_text: str, filename: str) -> int:
    """
    Chunk + embed teks mentah, lalu simpan ke tabel `documents`.
    Mengembalikan jumlah chunk yang berhasil disimpan.
    """
    if not raw_text.strip():
        raise ValueError("Dokumen tidak memiliki konten teks yang dapat diekstrak.")

    chunks = _splitter.split_text(raw_text)
    if not chunks:
        return 0

    vectors = embed_documents(chunks)

    for chunk_text, vector in zip(chunks, vectors):
        doc = Document(
            filename=filename,
            content=chunk_text,
            embedding=vector,
            metadata_={"source": filename},
        )
        db.add(doc)

    db.commit()
    return len(chunks)


def index_document(db: Session, file_path: str, filename: str) -> int:
    """
    Proses file dokumen (PDF/TXT/MD) menjadi chunk + embedding, simpan ke tabel `documents`.
    Mengembalikan jumlah chunk yang berhasil disimpan.
    """
    raw_text = _load_raw_text(file_path)
    return index_text(db, raw_text, filename)


# --- Pengelolaan knowledge base ---------------------------------------------
#
# Satu dokumen tersimpan sebagai beberapa baris `documents` yang berbagi
# `filename`. Fungsi di bawah memperlakukan filename sebagai identitas dokumen,
# sehingga pengelolaan terasa per-dokumen, bukan per-chunk.


def daftar_dokumen(db: Session) -> list[dict]:
    """Ringkasan seluruh dokumen: jumlah chunk, ukuran, dan waktu pembuatan."""
    stmt = (
        select(
            Document.filename,
            func.count(Document.id).label("chunks"),
            func.sum(func.length(Document.content)).label("karakter"),
            func.min(Document.created_at).label("dibuat"),
        )
        .group_by(Document.filename)
        .order_by(Document.filename)
    )
    return [
        {
            "filename": b.filename,
            "chunks": b.chunks,
            "characters": int(b.karakter or 0),
            "created_at": b.dibuat,
        }
        for b in db.execute(stmt).all()
    ]


def ambil_dokumen(db: Session, filename: str) -> str | None:
    """Gabungkan kembali seluruh chunk menjadi teks utuh untuk disunting."""
    stmt = (
        select(Document.content)
        .where(Document.filename == filename)
        .order_by(Document.id)
    )
    bagian = [b.content for b in db.execute(stmt).all()]
    if not bagian:
        return None
    return "\n\n".join(bagian)


def hapus_dokumen(db: Session, filename: str) -> int:
    """Hapus seluruh chunk milik satu dokumen. Mengembalikan jumlah yang dihapus."""
    hasil = db.execute(delete(Document).where(Document.filename == filename))
    db.commit()
    return hasil.rowcount or 0


def ganti_dokumen(db: Session, filename: str, raw_text: str) -> int:
    """
    Ganti isi dokumen: chunk lama dibuang, teks baru diindeks ulang.

    Dijalankan sebagai satu transaksi supaya dokumen tidak pernah berada dalam
    keadaan setengah terhapus bila proses embedding gagal di tengah jalan.
    """
    if not raw_text.strip():
        raise ValueError("Dokumen tidak memiliki konten teks yang dapat diekstrak.")

    potongan = _splitter.split_text(raw_text)
    if not potongan:
        raise ValueError("Tidak ada potongan teks yang dapat diindeks.")

    vektor = embed_documents(potongan)

    db.execute(delete(Document).where(Document.filename == filename))
    for isi, v in zip(potongan, vektor):
        db.add(Document(filename=filename, content=isi, embedding=v, metadata_={"source": filename}))
    db.commit()
    return len(potongan)


def hitung_chunk(db: Session, filename: str) -> int:
    return db.execute(
        select(func.count(Document.id)).where(Document.filename == filename)
    ).scalar_one()


def dokumen_ada(db: Session, filename: str) -> bool:
    return hitung_chunk(db, filename) > 0


def hitung_ulang_embedding(
    db: Session, ukuran_batch: int = 32, semua: bool = False
) -> dict:
    """
    Hitung embedding chunk tanpa mengubah teksnya.

    Secara bawaan hanya chunk yang BELUM punya embedding yang diproses — dokumen
    yang sudah terindeks tidak dihitung ulang percuma. Menghitung ulang seluruh
    knowledge base memakan waktu lama dan hanya perlu setelah embedding model
    diganti, jadi itu harus diminta secara eksplisit lewat `semua=True`.
    """
    stmt = select(Document.id, Document.content)
    if not semua:
        stmt = stmt.where(Document.embedding.is_(None))

    baris = list(db.execute(stmt).all())
    keseluruhan = db.execute(select(func.count(Document.id))).scalar_one()

    if not baris:
        return {"reindexed": 0, "skipped": keseluruhan, "total": keseluruhan}

    total = 0
    for i in range(0, len(baris), ukuran_batch):
        potongan = baris[i : i + ukuran_batch]
        vektor = embed_documents([b.content for b in potongan])
        for b, v in zip(potongan, vektor):
            db.query(Document).filter(Document.id == b.id).update({"embedding": v})
        db.commit()
        total += len(potongan)
    return {
        "reindexed": total,
        "skipped": keseluruhan - total,
        "total": keseluruhan,
    }
