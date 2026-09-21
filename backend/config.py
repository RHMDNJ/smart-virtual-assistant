"""
config.py
Konfigurasi aplikasi Smart Virtual Assistant.
Membaca environment variables dari .env menggunakan pydantic-settings.
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Akar project (satu tingkat di atas backend/). Dipakai untuk menormalkan path
# storage agar tidak bergantung pada direktori kerja saat proses dijalankan.
_BASE_DIR = Path(__file__).resolve().parent.parent

_DEFAULT_JWT_SECRET = "change-this-secret-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_ENV: str = "development"
    APP_NAME: str = "Smart Virtual Assistant"

    # Database
    DATABASE_URL: str = "postgresql://postgres:mysecretpassword@localhost:5432/agentic_rag"
    # Koneksi khusus SQL tool, memakai PostgreSQL user yang hanya punya SELECT
    # pada chat_stats & documents. Kosongkan untuk memakai DATABASE_URL (tidak disarankan).
    SQL_READONLY_DATABASE_URL: str = ""

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    # Harus model yang mendukung tool-calling (llama3 biasa TIDAK mendukung).
    OLLAMA_LLM_MODEL: str = "llama3.1"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIM: int = 768

    # Storage
    UPLOAD_DIR: str = "./storage/uploads"
    PROCESSED_DIR: str = "./storage/processed"
    MAX_UPLOAD_SIZE_MB: int = 20

    # RAG / retrieval
    RAG_TOP_K: int = 4               # jumlah chunk yang diberikan ke LLM
    RAG_CANDIDATE_K: int = 20        # kandidat yang diambil tiap retriever sebelum digabung
    RAG_HYBRID: bool = True          # gabungkan vector search dengan full-text search
    RAG_RRF_K: int = 60              # konstanta Reciprocal Rank Fusion
    RAG_FTS_CONFIG: str = "indonesian"

    # OCR
    OCR_LANG: str = "id"  # PaddleOCR: "id" (Indonesia), "en", dll.
    OCR_USE_ANGLE_CLS: bool = False  # klasifikasi orientasi baris; aktifkan jika gambar miring/terbalik

    # CORS
    # localhost dan 127.0.0.1 adalah origin berbeda bagi browser — sertakan keduanya
    # agar frontend tetap jalan apa pun host yang dipakai Vite.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Auth
    JWT_SECRET_KEY: str = _DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 8

    # SQL Tool safety
    # chat_stats = view metadata chat tanpa kolom `message` (lihat init_db).
    SQL_ALLOWED_TABLES: str = "chat_stats,documents"
    SQL_QUERY_TIMEOUT_SECONDS: int = 5

    @field_validator("UPLOAD_DIR", "PROCESSED_DIR")
    @classmethod
    def _jadikan_absolut(cls, v: str) -> str:
        """
        Path relatif diukur dari akar project, bukan dari CWD.

        Tanpa ini, `uvicorn` yang dijalankan dari backend/ menulis ke
        backend/storage/, sementara Docker dan .gitignore mengacu ke storage/
        di akar — dua lokasi berbeda untuk hal yang sama.
        """
        path = Path(v)
        return str(path if path.is_absolute() else (_BASE_DIR / path).resolve())

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def sql_allowed_tables_list(self) -> list[str]:
        return [t.strip() for t in self.SQL_ALLOWED_TABLES.split(",") if t.strip()]


settings = Settings()

# Kunci JWT default hanya boleh dipakai saat development. Di luar itu, gagal cepat
# daripada menandatangani token dengan rahasia yang diketahui publik.
if settings.APP_ENV != "development" and settings.JWT_SECRET_KEY == _DEFAULT_JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET_KEY masih memakai nilai default. Setel nilai acak yang rahasia "
        "sebelum menjalankan di luar development."
    )
