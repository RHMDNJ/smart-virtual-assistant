"""
sql_tool.py
Tool SQL — mengambil data terstruktur dari PostgreSQL (Bagian 8, Tool 3).

Mekanisme keamanan (Bagian 18):
- Hanya mengizinkan statement SELECT (read-only).
- Allowlist tabel yang boleh diakses.
- Query timeout.
- Tidak ada operasi DROP/DELETE/UPDATE/INSERT/ALTER/TRUNCATE.

Catatan: untuk produksi, gunakan juga database user PostgreSQL yang
benar-benar read-only (GRANT SELECT saja) sebagai lapisan pertahanan kedua,
karena validasi di level aplikasi ini tidak boleh menjadi satu-satunya kontrol.
"""

import re
from collections import OrderedDict

from langchain_core.tools import StructuredTool, tool
from sqlalchemy import text as sql_text
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from database import ReadOnlySessionLocal

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CREATE|EXECUTE|CALL|COPY)\b",
    re.IGNORECASE,
)

_BASE_DESCRIPTION = """Jalankan query SQL read-only (SELECT) ke database PostgreSQL untuk mengambil data
terstruktur, contoh: statistik chat history, jumlah dokumen, dsb.
Query destruktif (INSERT/UPDATE/DELETE/DROP/dll) akan ditolak."""

_schema_cache: str | None = None


class SQLValidationError(Exception):
    pass


def describe_allowed_schema() -> str:
    """
    Baca skema nyata (tabel + kolom) dari database untuk tabel yang di-allowlist.

    Tanpa ini, agent hanya tahu nama tabel dan cenderung mengarang kolom
    (mis. `WHERE user_id = ...` pada tabel yang tidak punya kolom tersebut).
    Hasilnya di-cache karena skema tidak berubah saat runtime.
    """
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache

    tables = settings.sql_allowed_tables_list

    db = ReadOnlySessionLocal()
    try:
        rows = db.execute(
            sql_text(
                """
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = ANY(:tables)
                ORDER BY table_name, ordinal_position
                """
            ),
            {"tables": tables},
        ).all()
    except SQLAlchemyError:
        # Jangan sampai kegagalan introspeksi menggagalkan pembuatan agent.
        return f"Tabel yang diizinkan: {', '.join(tables)} (skema tidak dapat dibaca)."
    finally:
        db.close()

    if not rows:
        return f"Tabel yang diizinkan: {', '.join(tables)} (tidak ada kolom terbaca)."

    grouped: "OrderedDict[str, list[str]]" = OrderedDict()
    for table_name, column_name, data_type in rows:
        grouped.setdefault(table_name, []).append(f"{column_name} {data_type}")

    lines = [f"- {t}({', '.join(cols)})" for t, cols in grouped.items()]
    _schema_cache = (
        "Hanya tabel dan kolom berikut yang tersedia:\n"
        + "\n".join(lines)
        + "\nGunakan HANYA kolom di atas. Jangan mengarang kolom yang tidak terdaftar "
        "(misalnya email atau departemen). Jika data yang diminta tidak ada kolomnya, katakan bahwa "
        "informasi tersebut tidak tersedia."
    )
    return _schema_cache


def validate_query(query: str) -> None:
    stripped = query.strip().rstrip(";")

    if not stripped.lower().startswith("select"):
        raise SQLValidationError("Hanya query SELECT yang diperbolehkan.")

    if ";" in stripped:
        raise SQLValidationError("Multiple statement tidak diperbolehkan.")

    if _FORBIDDEN_KEYWORDS.search(stripped):
        raise SQLValidationError("Query mengandung keyword yang tidak diperbolehkan.")

    allowed_tables = settings.sql_allowed_tables_list
    # Validasi sederhana: minimal salah satu tabel yang di-allowlist harus disebut di query.
    if not any(re.search(rf"\b{re.escape(table)}\b", stripped, re.IGNORECASE) for table in allowed_tables):
        raise SQLValidationError(
            f"Query harus mengakses salah satu tabel yang diizinkan: {', '.join(allowed_tables)}"
        )


def run_readonly_query(query: str) -> list[dict]:
    validate_query(query)

    db = ReadOnlySessionLocal()
    try:
        # Lapis kedua: meski user database sudah read-only, transaksi ini pun
        # ditandai read only supaya penulisan gagal sedini mungkin.
        db.execute(sql_text("SET TRANSACTION READ ONLY"))
        db.execute(sql_text(f"SET LOCAL statement_timeout = {settings.SQL_QUERY_TIMEOUT_SECONDS * 1000}"))
        result = db.execute(sql_text(query))
        rows = [dict(row._mapping) for row in result]
        return rows
    finally:
        db.close()


def _run_sql_query(query: str) -> str:
    try:
        rows = run_readonly_query(query)
    except SQLValidationError as exc:
        return f"Query ditolak: {exc}"
    except SQLAlchemyError as exc:
        # Sertakan skema agar agent dapat memperbaiki query pada percobaan berikutnya.
        return f"Query gagal dijalankan: {exc}\n\n{describe_allowed_schema()}"

    if not rows:
        return "Query berhasil dijalankan, tetapi tidak ada hasil."

    return str(rows)


def build_sql_tool() -> StructuredTool:
    """
    Buat tool sql_query dengan deskripsi yang memuat skema nyata database.

    Dibuat lewat factory (bukan dekorator @tool) karena deskripsinya perlu
    dibaca dari database saat runtime, bukan saat import module.
    """
    return StructuredTool.from_function(
        func=_run_sql_query,
        name="sql_query",
        description=f"{_BASE_DESCRIPTION}\n\n{describe_allowed_schema()}",
    )


@tool
def sql_query(query: str) -> str:
    """
    Jalankan query SQL read-only (SELECT) ke database PostgreSQL untuk mengambil data
    terstruktur, contoh: statistik chat history, jumlah dokumen, dsb.
    Query destruktif (INSERT/UPDATE/DELETE/DROP/dll) akan ditolak.

    Catatan: agent memakai versi dari build_sql_tool() yang deskripsinya memuat skema.
    Versi ini dipertahankan untuk pemakaian langsung/pengujian.
    """
    return _run_sql_query(query)
