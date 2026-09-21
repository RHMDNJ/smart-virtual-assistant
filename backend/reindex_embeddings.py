"""
reindex_embeddings.py
Hitung ulang seluruh embedding di tabel `documents`.

Dipakai saat berganti embedding model. Karena kolom `content` tetap tersimpan,
dokumen tidak perlu diunggah ulang. Jika dimensi model berbeda, kolom `embedding`
dibuat ulang beserta index HNSW-nya.

Contoh:
    OLLAMA_EMBEDDING_MODEL=bge-m3 EMBEDDING_DIM=1024 \
        .venv/bin/python reindex_embeddings.py
"""

import sys

from sqlalchemy import select, text

from config import settings
from database import SessionLocal, engine, terapkan_hak_readonly
from models import Document
from services.embedding_service import embed_documents

UKURAN_BATCH = 32


def dimensi_kolom_sekarang(conn) -> int | None:
    return conn.execute(
        text(
            "SELECT atttypmod FROM pg_attribute "
            "WHERE attrelid = 'documents'::regclass AND attname = 'embedding'"
        )
    ).scalar()


def buat_ulang_kolom(dim: int) -> None:
    with engine.connect() as conn:
        conn.execute(text("DROP INDEX IF EXISTS documents_embedding_hnsw_idx;"))
        conn.execute(text("ALTER TABLE documents DROP COLUMN IF EXISTS embedding;"))
        conn.execute(text(f"ALTER TABLE documents ADD COLUMN embedding vector({dim});"))
        conn.execute(
            text(
                "CREATE INDEX documents_embedding_hnsw_idx "
                "ON documents USING hnsw (embedding vector_cosine_ops);"
            )
        )
        # Kolom baru berarti hak akses perlu diberikan ulang.
        terapkan_hak_readonly(conn)
        conn.commit()


def main() -> int:
    dim = settings.EMBEDDING_DIM
    print(f"model    : {settings.OLLAMA_EMBEDDING_MODEL}")
    print(f"dimensi  : {dim}")

    with engine.connect() as conn:
        sekarang = dimensi_kolom_sekarang(conn)
    if sekarang != dim:
        print(f"kolom    : dimensi berubah ({sekarang} -> {dim}), kolom dibuat ulang")
        buat_ulang_kolom(dim)

    db = SessionLocal()
    try:
        baris = list(db.execute(select(Document.id, Document.content)).all())
        if not baris:
            print("tidak ada dokumen untuk diindeks ulang.")
            return 0

        total = 0
        for i in range(0, len(baris), UKURAN_BATCH):
            potongan = baris[i : i + UKURAN_BATCH]
            vektor = embed_documents([b.content for b in potongan])
            for b, v in zip(potongan, vektor):
                db.execute(
                    text("UPDATE documents SET embedding = CAST(:v AS vector) WHERE id = :id"),
                    {"v": "[" + ",".join(str(x) for x in v) + "]", "id": b.id},
                )
            db.commit()
            total += len(potongan)
            print(f"  {total}/{len(baris)} chunk")
        print("selesai.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
