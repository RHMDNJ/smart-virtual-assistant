"""
document_service.py
Pipeline RAG untuk indexing dokumen (Bagian 9 di README):
Document -> Loader -> Cleaning -> Chunking -> Embedding -> pgvector
"""

import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from models import Document
from services.embedding_service import embed_documents

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)


def _load_raw_text(file_path: str) -> str:
    """Load teks mentah dari file PDF/TXT. Untuk gambar, gunakan ocr_tool terlebih dahulu."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        return "\n\n".join(p.page_content for p in pages)

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


def hitung_ulang_embedding(db: Session, ukuran_batch: int = 32) -> int:
    """
    Hitung ulang embedding seluruh chunk tanpa mengubah teksnya.

    Dipakai setelah mengganti embedding model, atau bila indeks dicurigai basi.
    """
    baris = list(db.execute(select(Document.id, Document.content)).all())
    if not baris:
        return 0

    total = 0
    for i in range(0, len(baris), ukuran_batch):
        potongan = baris[i : i + ukuran_batch]
        vektor = embed_documents([b.content for b in potongan])
        for b, v in zip(potongan, vektor):
            db.query(Document).filter(Document.id == b.id).update({"embedding": v})
        db.commit()
        total += len(potongan)
    return total
