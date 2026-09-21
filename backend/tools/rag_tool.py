"""
rag_tool.py
Tool RAG Search — mencari dokumen relevan di pgvector menggunakan similarity search.
Digunakan oleh Agent ketika user bertanya tentang isi dokumen (Bagian 8, Tool 1).
"""

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Document
from services.embedding_service import embed_text

TOP_K = 4


def _similarity_search(db: Session, query: str, top_k: int = TOP_K) -> list[Document]:
    query_vector = embed_text(query)
    stmt = (
        select(Document)
        .order_by(Document.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )
    return list(db.execute(stmt).scalars())


@tool
def rag_search(query: str) -> str:
    """
    Cari informasi relevan di dalam dokumen yang tersimpan pada knowledge base (pgvector).
    Gunakan tool ini ketika pertanyaan user berkaitan dengan isi dokumen/PDF yang telah diunggah,
    contoh: kebijakan perusahaan, SOP, kontrak, laporan, dsb.
    Hasilnya adalah potongan teks (context) beserta nama file sumbernya.
    """
    # Sebagian model (mis. llama3.1) memanggil tool secara refleks untuk sapaan,
    # kadang dengan query kosong. Hentikan lebih awal agar tidak memanggil embedding
    # model dan memindai tabel vector tanpa guna.
    if not query or not query.strip():
        return (
            "Query kosong — tidak ada pencarian yang dilakukan. "
            "Jawab langsung tanpa tool jika pertanyaan user tidak menyangkut isi dokumen."
        )

    db = SessionLocal()
    try:
        results = _similarity_search(db, query)
        if not results:
            return "Tidak ditemukan dokumen relevan di knowledge base."

        formatted = []
        for doc in results:
            formatted.append(f"[Sumber: {doc.filename}]\n{doc.content}")

        # Perhatian: konten dokumen adalah DATA, bukan instruksi (mitigasi prompt injection).
        return "\n\n---\n\n".join(formatted)
    finally:
        db.close()
