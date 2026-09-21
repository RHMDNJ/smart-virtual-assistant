# Smart Virtual Assistant

Implementasi **Agentic RAG** lokal: FastAPI + LangChain + PostgreSQL/pgvector + PaddleOCR + Ollama + ViteJS/React.

Project ini adalah implementasi kode dari arsitektur dan roadmap fase yang dijelaskan di
[README-TECH-STACK.md](README-TECH-STACK.md).

## Struktur

```text
smart-virtual-assistant/
├── backend/                 # FastAPI + LangChain agent + tools (RAG, OCR, SQL)
├── frontend/                # Vite + React chat UI
├── storage/                 # Upload & processed files
├── docker-compose.yml
├── .env.example
├── README-TECH-STACK.md     # Dokumen arsitektur & roadmap fase
└── README.md                # Cara menjalankan + status implementasi
```

## Menjalankan — Development Lokal

### 1. Siapkan infrastruktur

```bash
# PostgreSQL + pgvector
docker run -d --name sva-db -p 5432:5432 \
  -e POSTGRES_PASSWORD=mysecretpassword \
  pgvector/pgvector:pg16

# Ollama (jalankan di host)
# PENTING: pakai model yang mendukung tool-calling. `llama3` biasa TIDAK mendukung,
# alternatif lain: qwen2.5, mistral-nemo.
ollama pull llama3.1
ollama pull nomic-embed-text
```

### 2. Backend

```bash
cd backend
uv venv --python 3.12 .venv                 # lihat catatan di bawah soal `python -m venv`
uv pip install --python .venv/bin/python -r requirements.txt
cp ../.env.example .env     # sesuaikan jika perlu
.venv/bin/uvicorn main:app --reload --port 8000
```

> **macOS**: gunakan `uv venv`, bukan `python3 -m venv`. Bottle `python@3.12` Homebrew
> pada macOS 26.x me-link `pyexpat` ke `/usr/lib/libexpat.1.dylib` sistem yang tidak
> punya simbol `_XML_SetAllocTrackerActivationThreshold`, sehingga `plistlib`, `xml.*`,
> dan `ensurepip`/pip ikut gagal. Python standalone dari `uv` tidak terpengaruh.

Cek: `http://localhost:8000/health` → `{"status": "ok"}`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Buka `http://localhost:5173`.

## Menjalankan — Docker Compose (Postgres + Backend)

> **Belum diverifikasi end-to-end.** Konfigurasi ini sudah diperbaiki dan lolos
> `docker compose config`, tetapi build image-nya tidak pernah diselesaikan: Docker
> sengaja tidak dipasang di mesin pengembangan (VM-nya memakan ~6 GB RAM, sementara
> Ollama juga butuh ~5–6 GB). Perlakukan sebagai titik awal untuk deployment, bukan
> jalur yang sudah terbukti. Untuk pengembangan lokal, pakai cara native di atas.

```bash
docker compose up -d --build
```

Frontend tetap dijalankan terpisah dengan `npm run dev` (atau tambahkan service frontend
sendiri jika ingin full containerized).

Beberapa hal yang sengaja berbeda dari setup lokal:

- **Tidak memakai `env_file: .env`.** Nilai di `.env` lokal memakai host `localhost`,
  yang di dalam container menunjuk container itu sendiri — bukan Postgres maupun Ollama.
  Compose menyetel nilai khusus container lewat blok `environment:`.
- **Ollama tetap di host** (`host.docker.internal:11434`), karena inference perlu akses
  GPU/Metal yang tidak tersedia di dalam container Linux.
- **Image `pgvector/pgvector:pg17`**, menyamai PostgreSQL 17 pada setup lokal.
- **`docker/initdb/01-readonly-user.sql`** membuat role `sva_readonly` saat data
  directory pertama kali dibuat. Pemberian `SELECT` per objek dilakukan aplikasi di
  `init_db()` setiap startup, sehingga bersifat deklaratif: objek baru tidak otomatis
  terbuka, dan objek yang dikeluarkan dari allowlist ikut tertutup.
- **Buat user aplikasi pertama** setelah container jalan:

  ```bash
  docker compose exec backend python create_user.py admin --role ADMIN
  ```

## Endpoint API

| Method | Path            | Keterangan                                        | Role minimal |
|--------|-----------------|---------------------------------------------------|--------------|
| GET    | `/health`       | Health check                                      | publik |
| POST   | `/auth/login`   | Login, mengembalikan JWT (form OAuth2)            | publik |
| GET    | `/auth/me`      | Identitas user saat ini                           | READ_ONLY |
| POST   | `/auth/users`   | Buat user baru                                    | ADMIN |
| POST   | `/chat`         | Kirim pertanyaan ke Agent (opsional: `image_id`)  | READ_ONLY |
| GET    | `/chat/history` | Riwayat chat per `session_id` (hanya milik sendiri) | READ_ONLY |
| POST   | `/documents`    | Tambah teks langsung ke knowledge base            | USER |
| POST   | `/upload`       | Upload dokumen (PDF/TXT/MD) atau gambar           | USER |

### Autentikasi

Semua endpoint selain `/health` dan `/auth/login` membutuhkan header
`Authorization: Bearer <token>`. Role bertingkat: `READ_ONLY` < `USER` < `ADMIN`.

Buat user pertama lewat CLI:

```bash
cd backend
.venv/bin/python create_user.py admin --role ADMIN
```

Riwayat chat terikat pada `user_id`, sehingga satu user tidak dapat membaca
percakapan user lain meskipun menebak `session_id` milik orang tersebut.

> `JWT_SECRET_KEY` default hanya boleh dipakai saat `APP_ENV=development`.
> Di luar itu aplikasi sengaja gagal start sampai nilainya diganti.

### Alur OCR

`POST /upload` untuk gambar mengembalikan `image_id`. Kirim id itu pada `POST /chat`
berikutnya — server menerjemahkannya ke path di `UPLOAD_DIR` (divalidasi agar tidak bisa
dipakai membaca file lain), lalu agent menjalankan `image_ocr`. Client tidak pernah
mengirim path file.

## Cara Kerja Agent

Agent (`backend/agent.py`) menggunakan LangChain **tool-calling agent** di atas LLM lokal (Ollama). Agent memilih salah satu dari tiga tool sesuai kebutuhan pertanyaan:

- **`rag_search`** — similarity search ke `documents` (pgvector) untuk pertanyaan tentang isi dokumen.
- **`image_ocr`** — PaddleOCR untuk membaca teks dari gambar yang diunggah.
- **`sql_query`** — query read-only ke PostgreSQL untuk data terstruktur (dengan allowlist tabel & validasi anti-destruktif).

Jika pertanyaan tidak membutuhkan tool, LLM menjawab langsung.

10 pesan terakhir pada `session_id` yang sama dikirim ulang sebagai `chat_history`,
sehingga agent dapat memahami pertanyaan lanjutan ("bagaimana dengan yang kedua?").

## Status Implementasi

Ini adalah **skeleton fungsional**, bukan sistem production-ready. Yang sudah diimplementasikan:

- [x] Struktur backend lengkap sesuai README arsitektur (config, database, models, schemas, services, tools, agent, main).
- [x] RAG pipeline: load PDF/TXT → chunking → embedding (Ollama) → simpan ke pgvector.
- [x] OCR tool berbasis PaddleOCR.
- [x] SQL tool read-only dengan validasi allowlist tabel & keyword destruktif.
- [x] Agent orchestrator LangChain tool-calling.
- [x] Endpoint `/health`, `/chat`, `/chat/history`, `/documents`, `/upload`.
- [x] Frontend chat minimal (Vite + React + Tailwind) dengan upload file.
- [x] Alur OCR end-to-end: upload gambar → `image_id` → pertanyaan → OCR → jawaban.
- [x] `tool_used` & `sources` terisi pada response (`return_intermediate_steps`).
- [x] Conversation memory per `session_id` (10 pesan terakhir).
- [x] Index HNSW (`vector_cosine_ops`) pada kolom embedding.
- [x] Authentication & Authorization: JWT + role ADMIN/USER/READ_ONLY, riwayat chat terisolasi per user.
- [x] Frontend: layar login, penyimpanan token, auto-logout saat token ditolak, tombol upload disembunyikan untuk READ_ONLY.
- [x] Validasi unggahan: ekstensi + MIME type + file signature (magic bytes), batas ukuran ditegakkan saat streaming.
- [x] SQL tool berjalan sebagai PostgreSQL user read-only (`sva_readonly`) dengan `SELECT` hanya pada `chat_stats` & `documents`.
- [x] Test otomatis: 81 test pytest.

Yang **belum** diimplementasikan (lihat roadmap di dokumen arsitektur, Bagian 18 & 25) dan perlu ditambahkan sebelum produksi:

- [ ] Streaming response, reranking, hybrid search, dsb (fitur lanjutan di Bagian 25).

### Hasil uji runtime (macOS 26.2, Apple M4)

| Uji | Hasil |
|---|---|
| `GET /health` | lolos |
| `POST /documents` → embedding → pgvector | lolos (`vector(768)`) |
| RAG-001 (pertanyaan isi dokumen) | lolos — `tool_used: rag_search`, `sources` terisi |
| Memori percakapan (pertanyaan lanjutan) | lolos |
| SQL-001 (statistik dari DB) | lolos — `tool_used: sql_query` |
| OCR-001 (upload gambar → `image_id` → `/chat`) | lolos — `tool_used: image_ocr` |
| SEC-001 (query destruktif) | lolos — DROP/DELETE/UPDATE/multi-statement/tabel non-allowlist ditolak |
| SEC-002 (informasi tidak ada) | lolos — menyatakan tidak ditemukan, tidak mengarang |
| Auth: endpoint tanpa token | lolos — `/chat`, `/chat/history`, `/documents`, `/upload` semua 401 |
| Auth: password salah / token palsu | lolos — 401 |
| Auth: role READ_ONLY | lolos — boleh `/chat`, ditolak 403 pada `/documents` dan `/auth/users` |
| Auth: isolasi riwayat antar user | lolos — admin melihat 0 entri untuk sesi milik user lain |
| Frontend: login, logout, sembunyi upload | lolos (diuji di Chrome) |
| AGENT-002 (pertanyaan ambigu) | lolos — "jam berapa masuk kerja" → `rag_search`, "berapa dokumen" → `sql_query` |
| SQL dengan skema | lolos — agent memakai kolom nyata (sebelumnya mengarang `user_id`) |
| AGENT-001 (pertanyaan umum) | **sebagian** — jawaban sudah benar & tanpa karangan, tetapi `llama3.1` masih memanggil `rag_search` |

Catatan AGENT-001: halusinasinya sudah hilang setelah system prompt dipertegas — sapaan
kini dijawab "Selamat pagi!" saja. Yang tersisa hanyalah panggilan tool yang mubazir
(`rag_search` dengan query kosong), dan itu refleks `llama3.1` saat tools di-bind, bukan
bug kode. `rag_tool` sudah menghentikan query kosong lebih awal agar tidak memanggil
embedding model. Perbaikan tuntas butuh model dengan disiplin tool lebih baik
(mis. `qwen2.5`).

## Testing

```bash
cd backend
uv pip install --python .venv/bin/python -r requirements-dev.txt
createdb -O postgres agentic_rag_test          # sekali saja
psql -d agentic_rag_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
.venv/bin/python -m pytest
```

54 test, selesai ~13 detik. Poin penting desainnya:

- **Database terpisah** (`agentic_rag_test`). `conftest.py` menolak jalan jika
  `DATABASE_URL` tidak mengandung kata `test`, dan mengosongkan tabel sebelum tiap test.
- **Ollama di-mock.** Test menguji API, auth, dan validasi — bukan kualitas jawaban
  model, yang lambat dan tidak deterministik. Kualitas model diuji terpisah secara manual.

Cakupan: auth & RBAC, isolasi riwayat antar user, validasi `image_id` (termasuk percobaan
path traversal), indexing dokumen, validasi upload, hashing password, allowlist SQL, dan
guard query kosong pada RAG.

### Perbandingan model: llama3.1 vs qwen2.5:7b

Diuji pada matriks yang sama (2026-09-22). Dua sel yang diperebutkan diulang 3x per model.

| Uji | llama3.1 | qwen2.5:7b |
|---|---|---|
| AGENT-001a (sapaan) | ❌ `rag_search` | ✅ `llm_direct` |
| AGENT-001b (tanya kemampuan) | ❌ `rag_search` | ✅ `llm_direct` |
| RAG-001 (isi dokumen) | ✅ benar | ✅ benar |
| AGENT-002 (jam masuk kerja) — 3x | ✅ 3/3 `rag_search`, jawaban benar | ❌ 3/3 `llm_direct`, **"informasi tidak tersedia"** |
| SQL-001 (jumlah dokumen) — 3x | ✅ 3/3 `sql_query`, jawaban benar | ❌ 3/3 `rag_search`, **jawaban salah** |
| OCR-001 (struk) | ✅ benar | ✅ benar |
| Kecepatan | 6–13 detik | 2–5 detik |

**Keputusan: tetap `llama3.1`.** qwen2.5 memang lebih disiplin untuk sapaan dan lebih
cepat, tetapi secara konsisten *terlalu hemat* memanggil tool: untuk pertanyaan yang
jawabannya jelas ada di knowledge base maupun di database, ia menjawab "informasi tidak
tersedia". Untuk sistem knowledge base, kegagalan itu jauh lebih merugikan daripada
panggilan RAG yang mubazir pada sapaan.

Catatan metodologi: satu sampel per sel sempat memberi kesimpulan terbalik (llama gagal
SQL-001, qwen lolos). Pengulangan 3x membalikkannya. Jangan ganti model berdasarkan
satu kali jalan.

### Catatan platform

- **Apple Silicon M4**: `paddlepaddle` 2.6.x **segfault** (SIGSEGV di kernel `sgemm`
  OpenBLAS bawaan `libphi.dylib` saat konvolusi) dan menjatuhkan seluruh proses uvicorn.
  Karena itu project ini memakai `paddlepaddle==3.3.1` + `paddleocr==3.7.0` dengan API
  `predict()`. Tidak ada env var OpenBLAS yang bisa menambal versi 2.6.x.
- **PaddleOCR 3.x mengunduh model dari HuggingFace** (PP-OCRv6), bukan dari
  `paddleocr.bj.bcebos.com`. Di jaringan yang memblokir HuggingFace, cache model
  (`~/.paddlex`) harus disiapkan lebih dulu.

## Keamanan — Catatan Penting

- **Prompt injection**: konten dokumen/OCR/SQL diperlakukan sebagai *data*, bukan instruksi, dan sistem prompt agent menegaskan hal ini secara eksplisit — namun ini bukan jaminan mutlak terhadap serangan canggih.
- **SQL tool — tiga lapis**: (1) validasi aplikasi menolak non-SELECT, multi-statement, dan tabel di luar allowlist; (2) agent hanya melihat view `chat_stats` yang tidak memuat kolom `message`, sehingga isi percakapan tidak terbaca; (3) koneksinya memakai PostgreSQL user `sva_readonly` yang secara privilege hanya bisa `SELECT` pada `chat_stats` dan `documents` — tabel `users` dan `chat_history` mentah ditolak oleh database itu sendiri.
- **File upload**: ekstensi, MIME type, dan file signature diperiksa sebelum apa pun ditulis ke disk; batas ukuran ditegakkan saat streaming sehingga unggahan raksasa tidak sempat memenuhi disk. Tambahkan antivirus scanning jika dipakai di lingkungan produksi.
- **Isolasi data**: riwayat chat terikat `user_id`; satu user tidak bisa membaca percakapan user lain, baik lewat `/chat/history`, lewat memori percakapan agent, maupun lewat `sql_query`.

### Menyiapkan user database read-only

```sql
CREATE ROLE sva_readonly LOGIN PASSWORD '<rahasia>';
GRANT CONNECT ON DATABASE agentic_rag TO sva_readonly;
GRANT USAGE ON SCHEMA public TO sva_readonly;
GRANT SELECT ON chat_stats, documents TO sva_readonly;
```

Lalu setel `SQL_READONLY_DATABASE_URL` di `.env`. Jika dikosongkan, SQL tool jatuh ke
koneksi utama yang punya hak tulis dan aplikasi mencatat peringatan saat start.
