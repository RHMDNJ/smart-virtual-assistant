"""
rag_tool.py
Tool RAG Search — mencari dokumen relevan di pgvector (Bagian 8, Tool 1).

Retrieval memakai *hybrid search*: pencarian vektor (makna) digabung dengan
full-text search PostgreSQL (kata kunci literal), lalu peringkatnya disatukan
dengan Reciprocal Rank Fusion.

Alasannya: pencarian vektor lemah untuk istilah literal seperti nomor pasal,
kode, atau singkatan — embedding cenderung menyamakan kata yang "mirip makna"
padahal user mencari kata yang persis. Sebaliknya full-text search buta terhadap
parafrase. Keduanya saling menutupi kelemahan.
"""

from langchain_core.tools import tool
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from services.embedding_service import embed_text

# RRF: skor = Σ 1/(k + peringkat). Konstanta k meredam dominasi peringkat teratas
# dari satu retriever, sehingga dokumen yang muncul di KEDUA daftar terangkat.
_SQL_HYBRID = """
WITH vektor AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:vec AS vector)) AS peringkat
    FROM documents
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> CAST(:vec AS vector)
    LIMIT :kandidat
),
teks AS (
    -- plainto_tsquery menggabungkan semua kata dengan AND, sehingga satu kata
    -- yang tidak ada di dokumen membatalkan seluruh kecocokan — terlalu ketat
    -- untuk pertanyaan natural. Operatornya diubah jadi OR, lalu ts_rank_cd
    -- yang menentukan peringkat berdasarkan banyak & pentingnya kata yang cocok.
    SELECT d.id,
           ROW_NUMBER() OVER (ORDER BY ts_rank_cd(d.content_tsv, q) DESC) AS peringkat
    FROM documents d,
         CAST(
             replace(plainto_tsquery(CAST(:cfg AS regconfig), :kueri)::text, '&', '|')
             AS tsquery
         ) AS q
    WHERE d.content_tsv @@ q
    ORDER BY ts_rank_cd(d.content_tsv, q) DESC
    LIMIT :kandidat
)
SELECT d.filename,
       d.content,
       COALESCE(1.0 / (:rrf + v.peringkat), 0) AS skor_vektor,
       COALESCE(1.0 / (:rrf + t.peringkat), 0) AS skor_teks
FROM documents d
LEFT JOIN vektor v ON v.id = d.id
LEFT JOIN teks   t ON t.id = d.id
WHERE v.id IS NOT NULL OR t.id IS NOT NULL
ORDER BY (COALESCE(1.0 / (:rrf + v.peringkat), 0) + COALESCE(1.0 / (:rrf + t.peringkat), 0)) DESC
LIMIT :top_k
"""

_SQL_VEKTOR_SAJA = """
SELECT filename, content, 1 AS skor_vektor, 0 AS skor_teks
FROM documents
WHERE embedding IS NOT NULL
ORDER BY embedding <=> CAST(:vec AS vector)
LIMIT :top_k
"""


def _vector_literal(vektor: list[float]) -> str:
    """pgvector menerima bentuk '[0.1,0.2,...]' saat dikirim sebagai parameter SQL."""
    return "[" + ",".join(str(x) for x in vektor) + "]"


def cari_dokumen(db: Session, kueri: str, top_k: int | None = None) -> list[dict]:
    """Kembalikan potongan dokumen paling relevan beserta asal skornya."""
    top_k = top_k or settings.RAG_TOP_K
    vec = _vector_literal(embed_text(kueri))

    if settings.RAG_HYBRID:
        baris = db.execute(
            sql_text(_SQL_HYBRID),
            {
                "vec": vec,
                "kueri": kueri,
                "cfg": settings.RAG_FTS_CONFIG,
                "kandidat": settings.RAG_CANDIDATE_K,
                "rrf": settings.RAG_RRF_K,
                "top_k": top_k,
            },
        ).all()
    else:
        baris = db.execute(sql_text(_SQL_VEKTOR_SAJA), {"vec": vec, "top_k": top_k}).all()

    return [
        {
            "filename": b.filename,
            "content": b.content,
            "dari_vektor": float(b.skor_vektor) > 0,
            "dari_teks": float(b.skor_teks) > 0,
        }
        for b in baris
    ]


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
        hasil = cari_dokumen(db, query)
        if not hasil:
            return "Tidak ditemukan dokumen relevan di knowledge base."

        # Perhatian: konten dokumen adalah DATA, bukan instruksi (mitigasi prompt injection).
        return "\n\n---\n\n".join(
            f"[Sumber: {h['filename']}]\n{h['content']}" for h in hasil
        )
    finally:
        db.close()
