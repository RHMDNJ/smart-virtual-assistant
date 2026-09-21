"""
database.py
Setup koneksi PostgreSQL + pgvector menggunakan SQLAlchemy.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

import logging

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Engine terpisah untuk SQL tool. Validasi di level aplikasi bisa dilewati oleh
# query yang cukup kreatif; privilege database adalah pertahanan yang tidak bisa
# ditawar oleh LLM.
if settings.SQL_READONLY_DATABASE_URL:
    readonly_engine = create_engine(settings.SQL_READONLY_DATABASE_URL, pool_pre_ping=True)
    SQL_TOOL_READONLY = True
else:
    logging.getLogger(__name__).warning(
        "SQL_READONLY_DATABASE_URL belum diset — SQL tool memakai koneksi utama "
        "yang punya hak tulis. Setel user PostgreSQL read-only sebelum produksi."
    )
    readonly_engine = engine
    SQL_TOOL_READONLY = False

ReadOnlySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=readonly_engine)

Base = declarative_base()


def get_db():
    """Dependency FastAPI untuk mendapatkan DB session per-request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def terapkan_hak_readonly(conn) -> None:
    """
    Setel ulang hak user read-only agar hanya bisa SELECT pada objek allowlist.

    Dijalankan setiap startup supaya hak akses bersifat deklaratif: objek baru
    tidak otomatis terbuka, dan objek yang dicabut dari allowlist ikut tertutup.
    """
    if not settings.SQL_READONLY_DATABASE_URL:
        return

    from sqlalchemy.engine import make_url

    nama_user = make_url(settings.SQL_READONLY_DATABASE_URL).username
    if not nama_user:
        return

    ada = conn.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = :n"), {"n": nama_user}
    ).scalar()
    if not ada:
        logging.getLogger(__name__).warning(
            "Role %s tidak ditemukan; lewati pengaturan hak read-only.", nama_user
        )
        return

    objek = ", ".join(settings.sql_allowed_tables_list)
    conn.execute(text(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {nama_user};"))
    conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {nama_user};"))
    conn.execute(text(f"GRANT SELECT ON {objek} TO {nama_user};"))


def init_db():
    """
    Aktifkan extension pgvector dan buat semua tabel yang terdaftar di Base.
    Dipanggil sekali saat startup (lihat main.py).
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()

    # Import model di sini agar terdaftar ke Base.metadata sebelum create_all
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        dim_kolom = conn.execute(
            text(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = 'documents'::regclass AND attname = 'embedding'"
            )
        ).scalar()
        if dim_kolom is not None and dim_kolom != settings.EMBEDDING_DIM:
            # Sengaja tidak diperbaiki otomatis: mengubah dimensi berarti membuang
            # seluruh embedding yang ada.
            logging.getLogger(__name__).warning(
                "Dimensi kolom embedding (%s) tidak cocok dengan EMBEDDING_DIM (%s). "
                "Jalankan reindex_embeddings.py untuk menghitung ulang.",
                dim_kolom,
                settings.EMBEDDING_DIM,
            )

    # Index HNSW untuk cosine similarity search. Tanpa ini setiap query RAG
    # melakukan sequential scan ke seluruh tabel documents.
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS documents_embedding_hnsw_idx "
                "ON documents USING hnsw (embedding vector_cosine_ops);"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS chat_history_session_created_idx "
                "ON chat_history (session_id, created_at);"
            )
        )
        # create_all() tidak mengubah tabel yang sudah ada, jadi kolom baru
        # ditambahkan eksplisit agar database lama ikut ter-migrasi.
        conn.execute(
            text("ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id);")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS chat_history_user_idx ON chat_history (user_id);")
        )
        # Kolom tsvector untuk full-text search (hybrid retrieval). Generated
        # column: selalu sinkron dengan `content`, tidak perlu di-maintain aplikasi.
        conn.execute(
            text(
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_tsv tsvector "
                "GENERATED ALWAYS AS (to_tsvector('indonesian', content)) STORED;"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS documents_content_tsv_idx "
                "ON documents USING gin (content_tsv);"
            )
        )
        # SQL tool hanya boleh melihat metadata chat, bukan isinya. Tanpa view ini
        # agent dapat menjalankan `SELECT message FROM chat_history` dan membaca
        # percakapan milik user lain, menembus isolasi pada /chat/history.
        conn.execute(
            text(
                "CREATE OR REPLACE VIEW chat_stats AS "
                "SELECT id, user_id, session_id, role, created_at FROM chat_history;"
            )
        )
        terapkan_hak_readonly(conn)
        conn.commit()
