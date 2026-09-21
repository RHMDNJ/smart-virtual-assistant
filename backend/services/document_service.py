"""
document_service.py
Pipeline RAG untuk indexing dokumen (Bagian 9 di README):
Document -> Loader -> Cleaning -> Chunking -> Embedding -> pgvector
"""

import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
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
