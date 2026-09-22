# SAVIRA — Smart Virtual Assistant

<img src="frontend/public/brand/maskot-256.png" alt="" width="96" align="right" />

**SAVIRA** (Smart Virtual Assistant) adalah asisten digital **Pemerintah Kabupaten
Hulu Sungai Selatan**, berjalan sepenuhnya di infrastruktur lokal.

Implementasi **Agentic RAG** lokal: FastAPI + LangChain + PostgreSQL/pgvector + PaddleOCR + Ollama + ViteJS/React.

Project ini adalah implementasi kode dari arsitektur dan roadmap fase yang dijelaskan di
[README-TECH-STACK.md](README-TECH-STACK.md).

## Identitas visual

Aset brand ada di `frontend/public/brand/`:

| Berkas | Dipakai untuk |
|---|---|
| `maskot-32/64/180/192/512.png` | favicon, ikon PWA, avatar assistant, empty state |
| `banner-terang.webp` / `banner-gelap.webp` | latar layar login (mengikuti tema sistem) |
| `banner-maskot.webp` | cadangan, belum dipakai |

Palet diambil langsung dari logo Helpdesk HSS: navy `#001848`, biru `#0060d8`,
cyan `#00d8f0`.

Wordmark "SAVIRA" ditulis sebagai teks, bukan gambar. Logo raster harus
di-invert agar terbaca di mode gelap, dan filter itu mengubah maskot menjadi
siluet putih tanpa wajah — teks tetap tajam di ukuran apa pun dan mengikuti tema.

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

## Melihat aplikasi dikemudikan sendiri

```bash
cd backend && .venv/bin/python ../scripts/demo_browser.py
```

Membuka jendela Chrome sungguhan lalu menelusuri aplikasi sendiri — login,
bertanya ke dokumen, bertanya statistik, menyapa, dan keluar — dengan kursor
semu, sorotan elemen, dan label langkah agar prosesnya bisa diikuti.

`scripts/cdp_driver.py` memakai Chrome yang sudah terpasang lewat Chrome
DevTools Protocol, jadi tidak perlu Playwright yang mengunduh browser sendiri.
Set `headless=True` pada `cdp.launch()` untuk menjalankannya tanpa jendela
(dipakai pada pengujian otomatis).

## Menjalankan — dari VSCode

Tekan **F5** dan pilih salah satu konfigurasi di `.vscode/launch.json`:

| Konfigurasi | Yang terjadi |
|---|---|
| **Aplikasi di Chrome** | Menjalankan backend + frontend, lalu membuka Chrome dengan debugger ter-attach (breakpoint di `.jsx` langsung aktif) |
| **Backend (debug Python)** | Backend saja, dengan breakpoint Python lewat debugpy |
| **Backend + Chrome** | Keduanya sekaligus; berhenti bersamaan |

Task tersedia lewat **Terminal → Run Task**: `backend`, `frontend`, `stack`,
`test`, dan `hentikan stack`. Task `stack` menunggu kedua server benar-benar
siap (mendeteksi "Application startup complete" dan "ready in") sebelum Chrome
dibuka, sehingga tidak mendarat di halaman kosong.

Prasyarat tetap sama: PostgreSQL dan Ollama harus sudah jalan
(`brew services start postgresql@17 ollama`).

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
| POST   | `/chat/stream`  | Sama, tetapi jawaban dialirkan via SSE            | READ_ONLY |
| GET    | `/chat/history` | Riwayat chat per `session_id` (hanya milik sendiri) | READ_ONLY |
| GET    | `/documents`    | Daftar dokumen beserta jumlah bagian & ukuran     | READ_ONLY |
| GET    | `/documents/{nama}` | Isi utuh satu dokumen (chunk digabung kembali) | READ_ONLY |
| POST   | `/documents`    | Tambah dokumen baru (409 bila nama sudah ada)     | USER |
| PUT    | `/documents/{nama}` | Ganti isi dokumen, indeks ulang otomatis      | USER |
| DELETE | `/documents/{nama}` | Hapus dokumen dari knowledge base             | ADMIN |
| POST   | `/documents/reindex` | Hitung ulang embedding seluruh bagian        | ADMIN |
| POST   | `/upload`       | Upload dokumen (PDF/TXT/MD) atau gambar           | USER |

### Streaming (`/chat/stream`)

Mengembalikan Server-Sent Events:

```
data: {"type": "tool",  "name": "rag_search"}
data: {"type": "token", "text": "Menurut "}
data: {"type": "done",  "answer": "...", "tool_used": "rag_search", "sources": [...]}
```

Karena header sudah terkirim saat streaming dimulai, kegagalan di tengah jalan
dikirim sebagai `{"type": "error"}`, bukan sebagai HTTP error code.

**Kenapa dua fase.** Ollama tidak mengalirkan konten ketika tools di-bind — diuji
pada `langchain-ollama` 0.1.3 maupun 1.1.0, keduanya menghasilkan nol chunk teks,
jadi ini bukan soal versi. Karena itu `/chat/stream` memakai dua panggilan:
pemilihan tool (tidak streaming), lalu sintesis jawaban tanpa tools yang bisa
streaming. Tidak ada generasi ganda — panggilan kedua menggantikan sintesis yang
biasanya dilakukan AgentExecutor.

Konsekuensinya satu putaran tool per pertanyaan. `/chat` tetap memakai
AgentExecutor dan mendukung multi-putaran, tetapi tanpa streaming.

Terukur pada llama3.1: token pertama tiba ~6,6 detik (sebelumnya user menunggu
~9 detik tanpa umpan balik apa pun), 42 token mengalir sampai detik ke-8,7.

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

## Melatih SAVIRA — kelola knowledge base

Tombol **Knowledge base** di header membuka panel pengelolaan. Bagi sistem RAG,
inilah bentuk "melatih" yang sebenarnya: mengganti bahan bacaan asisten, bukan
melatih ulang bobot model.

- **Lihat** seluruh dokumen beserta jumlah bagian, ukuran, dan tanggal.
- **Tulis** dokumen langsung dari UI, atau **unggah** PDF/TXT/MD.
- **Sunting** isi dokumen; chunk lama dibuang dan teks baru diindeks ulang dalam
  satu transaksi, sehingga dokumen tidak pernah setengah terhapus bila embedding
  gagal di tengah jalan.
- **Hapus** dokumen (khusus ADMIN, dengan konfirmasi).
- **Indeks ulang** seluruh bagian setelah berganti embedding model (khusus ADMIN).

Dua perilaku yang dipilih sengaja:

- `POST /documents` menolak nama yang sudah ada (409) dan mengarahkan ke `PUT`.
  Tanpa ini, menyimpan dua kali diam-diam menghasilkan dokumen kembar yang
  saling bersaing saat retrieval.
- Mengunggah berkas dengan nama sama berarti **memperbarui**, bukan menduplikasi.

Kenapa bukan fine-tuning: melatih ulang bobot model perlu ratusan hingga ribuan
contoh, komputasi berjam-jam, dan hasilnya sering kalah dibanding RAG yang
datanya rapi. Mengganti dokumen berdampak seketika dan bisa ditarik kembali.

### PDF hasil pindai

PDF pindaian hanyalah gambar yang dibungkus PDF — tidak punya lapisan teks,
sehingga sebelumnya ditolak dengan pesan "tidak memiliki konten teks", padahal
isinya terbaca jelas oleh mata. Dokumen pemerintah kerap berbentuk demikian.

Kini halaman yang tidak memuat teks di-render lewat PyMuPDF lalu dibaca
PaddleOCR. Hanya halaman kosong yang di-OCR, jadi PDF campuran (sebagian teks,
sebagian pindaian) tetap utuh dan tidak membayar ongkos OCR dua kali.

Satu halaman yang gagal di-OCR dicatat sebagai peringatan dan dilewati, bukan
membatalkan seluruh dokumen. Pengaturan di `.env`: `OCR_PDF_FALLBACK`,
`OCR_PDF_MAX_PAGES` (bawaan 20, agar dokumen tebal tidak menggantung request),
dan `OCR_PDF_DPI`.

## Retrieval — Hybrid Search

`rag_search` menggabungkan dua pencarian lalu menyatukan peringkatnya dengan
**Reciprocal Rank Fusion**:

- **Vector search** (pgvector, cosine) menangkap kemiripan makna/parafrase.
- **Full-text search** PostgreSQL dengan konfigurasi `indonesian` menangkap kata
  kunci literal. Stemming-nya bekerja untuk Bahasa Indonesia: "kebijakan" → `bijak`,
  "perusahaan" → `usaha`, "karyawan" → `karyaw`.

Kolom `content_tsv` adalah *generated column*, jadi selalu sinkron dengan `content`
tanpa perlu dipelihara aplikasi, dengan index GIN di atasnya.

Satu catatan implementasi: `plainto_tsquery` menggabungkan semua kata dengan AND,
sehingga satu kata yang tidak ada di dokumen membatalkan seluruh kecocokan —
terlalu ketat untuk pertanyaan natural. Operatornya diubah menjadi OR, dan
`ts_rank_cd` yang menentukan peringkat.

### Hasil pengukuran

`backend/seed_korpus.py` mengisi 12 dokumen sintetis, `backend/eval_retrieval.py`
mengukur recall@3 atas 14 pertanyaan:

| embedding | mode | literal | parafrase | total |
|---|---|---|---|---|
| nomic-embed-text (768) | vektor saja | 6/6 | 4/8 | 10/14 (71%) |
| nomic-embed-text (768) | hybrid | 6/6 | 5/8 | 11/14 (79%) |
| **bge-m3 (1024)** | vektor saja | 6/6 | 8/8 | **14/14 (100%)** |
| **bge-m3 (1024)** | hybrid | 6/6 | 8/8 | **14/14 (100%)** |

Dua temuan yang penting dicatat.

**Pertama**, dugaan bahwa hybrid menolong pada istilah literal (nomor peraturan,
singkatan seperti HPS/TAPD/KIB) **tidak terbukti** — pencarian vektor sudah 6/6
di sana. Perbaikannya hanya satu kasus parafrase.

**Kedua**, batas sebenarnya ada pada embedding model, bukan pada metode
retrieval. Mengganti `nomic-embed-text` dengan `bge-m3` menaikkan recall dari
71% ke 100% dan menghapus seluruh kegagalan parafrase — jauh melampaui dampak
hybrid search. Hybrid tetap dipertahankan karena murah dan menolong pada korpus
besar dengan istilah literal langka, tetapi pemilihan embedding model adalah
tuas yang jauh lebih besar.

Ganti embedding model dengan `backend/reindex_embeddings.py` (dokumen tidak perlu
diunggah ulang karena `content` tersimpan):

```bash
OLLAMA_EMBEDDING_MODEL=bge-m3 EMBEDDING_DIM=1024 .venv/bin/python reindex_embeddings.py
```

Parameter di `.env`: `RAG_TOP_K`, `RAG_CANDIDATE_K`, `RAG_HYBRID`, `RAG_RRF_K`,
`RAG_FTS_CONFIG`.

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
- [x] Streaming response via SSE (`/chat/stream`) dengan kursor mengetik di UI.
- [x] UI: token warna terang/gelap mengikuti sistem, animasi masuk pesan, indikator
      berpikir, auto-scroll, textarea tumbuh otomatis, dan `prefers-reduced-motion`
      dihormati.
- [x] Pemulihan tool call yang keluar sebagai teks (lihat catatan di bawah).
- [x] Hybrid search (vector + full-text Indonesia) dengan Reciprocal Rank Fusion.
- [x] Embedding bge-m3 (recall@3 pada korpus uji: 71% -> 100%).
- [x] Pengelolaan knowledge base lewat UI (lihat, tulis, sunting, hapus, indeks ulang).
- [x] PDF hasil pindai dibaca lewat OCR per-halaman.
- [x] Test otomatis: 171 test pytest.

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
| AGENT-001 (sapaan) | lolos — `llm_direct`, "Selamat pagi! Semoga hari Anda menyenangkan!" |

### Tool call berbentuk teks

`llama3.1` kadang tidak mengisi `tool_calls` dan malah menuliskan panggilannya
sebagai JSON biasa di dalam konten:

```json
{"name": "sql_query", "parameters": {"query": "SELECT ..."}}
```

Tanpa penanganan, JSON itu tampil sebagai jawaban **dan** tersimpan ke riwayat,
lalu meracuni pemilihan tool pada pertanyaan berikutnya — inilah penyebab
kegagalan RAG-001 dan SQL-001 yang hanya muncul di browser (sesi panjang),
tidak pernah pada uji API bersesi baru. `_tool_call_dari_teks` memulihkannya
menjadi panggilan tool yang sebenarnya.

### Bertanya tentang berkas yang baru diunggah

Ketika user mengunggah dokumen lalu bertanya "apa isi dokumennya?", pencarian
**dibatasi pada berkas itu saja** (`document_filename` pada `POST /chat/stream`).

Tanpa pembatasan ini, pertanyaan yang sangat umum seperti itu punya kemiripan
vektor yang lemah terhadap dokumen mana pun, sehingga potongan dari dokumen lain
ikut terambil dan menenggelamkan berkas yang baru diunggah — dokumennya muncul
di daftar sumber, tetapi jawabannya "tidak ditemukan".

Untuk mode terbatas, `RAG_DOC_TOP_K` (bawaan 12) dipakai menggantikan
`RAG_TOP_K`, agar dokumen pendek terbaca utuh dan bisa diringkas.

### Riwayat bukan sumber fakta

Pada sesi berriwayat panjang, model terbukti **menyalin angka dari jawabannya
sendiri di masa lalu** — termasuk angka yang keliru — alih-alih memakai hasil
tool pada giliran itu. Ini menghasilkan jawaban yang salah tapi terdengar yakin,
jauh lebih berbahaya daripada menjawab "tidak ditemukan".

Dua penangkalnya:

- System prompt menegaskan riwayat hanya untuk memahami rujukan ("itu", "yang
  tadi"), bukan sumber fakta.
- Sebelum sintesis, pengingat disisipkan **ke dalam hasil tool terakhir**.
  Percobaan pertama memakai `SystemMessage` di akhir percakapan, dan itu membuat
  llama3.1 menuliskan penanda peran `assistant` ke dalam jawabannya.

Selain itu, bila `sql_query` tidak mengembalikan apa pun, sistem mencoba sekali
lagi lewat `rag_search` sebelum menyerah — llama3.1 kerap memilih SQL untuk
pertanyaan yang jawabannya ada di dokumen.

Terukur pada sesi dengan 251 pesan: sebelum perbaikan jawaban benar hanya 1 dari
3 percobaan (sisanya mengarang "08.00–15.00" dan "buka 24 jam"); sesudahnya 5
dari 5 benar, dan pertanyaan statistik tetap memakai SQL.

### Perutean sapaan

`llama3.1` refleks memanggil tool begitu tools di-bind. Selama knowledge base
masih kecil dampaknya hanya satu langkah mubazir, tetapi setelah berisi 12
dokumen, RAG mengembalikan potongan tak nyambung dan model menjawab *"Tidak ada
jawaban yang relevan untuk 'Selamat pagi!'"* — cacat yang terlihat user,
ditemukan lewat UAT di browser.

Mempertegas system prompt sudah dicoba dan tidak cukup. Karena itu pesan yang
**seluruhnya** berupa sapaan dirutekan lebih awal tanpa melibatkan tool, memakai
system prompt terpisah (`PROMPT_SAPAAN`). Polanya terjangkar sampai akhir
kalimat, sehingga "Halo, berapa sisa cuti?" tetap masuk jalur RAG.

## Testing

```bash
cd backend
uv pip install --python .venv/bin/python -r requirements-dev.txt
createdb -O postgres agentic_rag_test          # sekali saja
psql -d agentic_rag_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
.venv/bin/python -m pytest
```

171 test, selesai ~29 detik. Poin penting desainnya:

- **Database terpisah** (`agentic_rag_test`). `conftest.py` menolak jalan jika
  `DATABASE_URL` tidak mengandung kata `test`, dan mengosongkan tabel sebelum tiap test.
- **Ollama di-mock.** Test menguji API, auth, dan validasi — bukan kualitas jawaban
  model, yang lambat dan tidak deterministik. Kualitas model diuji terpisah secara manual.

Cakupan: auth & RBAC, isolasi riwayat antar user, validasi `image_id` (termasuk percobaan
path traversal), indexing dokumen, validasi upload, hashing password, allowlist SQL, dan
guard query kosong pada RAG, serta endpoint streaming (urutan event, penyimpanan
riwayat setelah stream selesai, dan kegagalan di tengah stream).

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
