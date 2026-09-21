"""
main.py
Entry point FastAPI — Smart Virtual Assistant (Agentic RAG).
Endpoint sesuai desain API di README (Bagian 13 & 20).
"""

import json
import os
import re
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent import run_agent, run_agent_stream
from config import settings
from database import SessionLocal, get_db, init_db
from models import ChatHistory, User
from schemas import (
    ChatHistoryItem,
    ChatRequest,
    ChatResponse,
    CreateUserRequest,
    DocumentRequest,
    DocumentResponse,
    HealthResponse,
    SourceItem,
    TokenResponse,
    UploadResponse,
    UserResponse,
)
from security import (
    ROLE_ADMIN,
    ROLE_READ_ONLY,
    ROLE_USER,
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
)
from file_validation import (
    BYTE_HEADER,
    FileValidationError,
    simpan_dengan_batas,
    validasi_unggahan,
)
from services.document_service import index_document, index_text

# Jumlah pesan terakhir yang disertakan sebagai memori percakapan ke agent.
HISTORY_WINDOW = 10

# image_id selalu dihasilkan server: 32 hex + ekstensi gambar.
_IMAGE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}\.(png|jpg|jpeg|webp)$")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
    init_db()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


def _resolve_image_path(image_id: str) -> str:
    """
    Terjemahkan `image_id` dari client menjadi path file di UPLOAD_DIR.

    Client tidak pernah mengirim path, hanya id yang dibuat server, dan hasilnya
    diverifikasi tetap berada di dalam UPLOAD_DIR (mencegah path traversal).
    """
    if not _IMAGE_ID_PATTERN.match(image_id):
        raise HTTPException(status_code=400, detail="image_id tidak valid.")

    upload_root = os.path.realpath(settings.UPLOAD_DIR)
    candidate = os.path.realpath(os.path.join(upload_root, image_id))

    if os.path.commonpath([upload_root, candidate]) != upload_root:
        raise HTTPException(status_code=400, detail="image_id tidak valid.")

    if not os.path.isfile(candidate):
        raise HTTPException(status_code=404, detail="Gambar tidak ditemukan. Unggah ulang file.")

    return candidate


def _load_history(db: Session, session_id: str, user_id: int) -> list[tuple[str, str]]:
    """Ambil N pesan terakhir pada session sebagai memori percakapan (urut lama → baru)."""
    stmt = (
        select(ChatHistory.role, ChatHistory.message)
        .where(ChatHistory.session_id == session_id)
        .where(ChatHistory.user_id == user_id)
        .where(ChatHistory.role.in_(("user", "assistant")))
        .order_by(ChatHistory.created_at.desc(), ChatHistory.id.desc())
        .limit(HISTORY_WINDOW)
    )
    rows = list(db.execute(stmt))
    return [(row.role, row.message) for row in reversed(rows)]


@app.post("/auth/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form.username, form.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Username atau password salah.")
    return TokenResponse(
        access_token=create_access_token(user.username, user.role),
        role=user.role,
        username=user.username,
    )


@app.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


@app.post("/auth/users", response_model=UserResponse)
def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(ROLE_ADMIN)),
):
    """Buat user baru. Hanya ADMIN."""
    if request.role not in (ROLE_READ_ONLY, ROLE_USER, ROLE_ADMIN):
        raise HTTPException(status_code=400, detail=f"Role tidak dikenal: {request.role}")

    sudah_ada = db.execute(select(User).where(User.username == request.username)).scalar_one_or_none()
    if sudah_ada is not None:
        raise HTTPException(status_code=409, detail="Username sudah dipakai.")

    try:
        password_hash = hash_password(request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = User(username=request.username, password_hash=password_hash, role=request.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(ROLE_READ_ONLY)),
):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message tidak boleh kosong.")

    image_path = _resolve_image_path(request.image_id) if request.image_id else None

    # Riwayat diambil sebelum pesan baru disimpan agar tidak terduplikasi dengan `input`.
    history = _load_history(db, request.session_id, user.id)

    db.add(
        ChatHistory(
            user_id=user.id, session_id=request.session_id, role="user", message=request.message
        )
    )
    db.commit()

    result = run_agent(request.message, image_path=image_path, chat_history=history)

    # Simpan jawaban assistant
    db.add(
        ChatHistory(
            user_id=user.id, session_id=request.session_id, role="assistant", message=result["answer"]
        )
    )
    db.commit()

    return ChatResponse(
        answer=result["answer"],
        tool_used=result["tool_used"],
        sources=[SourceItem(**s) for s in result["sources"]],
    )


def _simpan_pesan(session_id: str, user_id: int, role: str, message: str) -> None:
    db = SessionLocal()
    try:
        db.add(ChatHistory(user_id=user_id, session_id=session_id, role=role, message=message))
        db.commit()
    finally:
        db.close()


@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(ROLE_READ_ONLY)),
):
    """
    Versi streaming dari /chat, memakai Server-Sent Events.

    Dipisah dari /chat agar klien yang butuh satu respons utuh (dan seluruh
    test kontrak API) tetap bisa memakai endpoint lama tanpa perubahan.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message tidak boleh kosong.")

    image_path = _resolve_image_path(request.image_id) if request.image_id else None
    history = await run_in_threadpool(_load_history, db, request.session_id, user.id)
    await run_in_threadpool(
        _simpan_pesan, request.session_id, user.id, "user", request.message
    )

    async def penghasil_event():
        jawaban = ""
        try:
            async for event in run_agent_stream(
                request.message, image_path=image_path, chat_history=history
            ):
                if event["type"] == "done":
                    jawaban = event["answer"]
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            # Stream sudah dimulai, jadi kegagalan disampaikan sebagai event,
            # bukan sebagai HTTP error code.
            yield f'data: {json.dumps({"type": "error", "detail": str(exc)})}\n\n'
        finally:
            if jawaban:
                await run_in_threadpool(
                    _simpan_pesan, request.session_id, user.id, "assistant", jawaban
                )

    return StreamingResponse(
        penghasil_event(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/chat/history", response_model=list[ChatHistoryItem])
def chat_history(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(ROLE_READ_ONLY)),
):
    stmt = (
        select(ChatHistory)
        .where(ChatHistory.session_id == session_id)
        .where(ChatHistory.user_id == user.id)
        .order_by(ChatHistory.created_at.asc())
    )
    return list(db.execute(stmt).scalars())


@app.post("/documents", response_model=DocumentResponse)
def create_document(
    request: DocumentRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role(ROLE_USER)),
):
    """Tambahkan teks langsung ke knowledge base tanpa upload file."""
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content tidak boleh kosong.")

    try:
        chunk_count = index_text(db, request.content, request.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Gagal mengindeks dokumen: {exc}") from exc

    return DocumentResponse(filename=request.filename, status="indexed", chunks=chunk_count)


@app.post("/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(ROLE_USER)),
):
    # Periksa ekstensi, MIME, dan file signature SEBELUM apa pun ditulis ke disk.
    header = file.file.read(BYTE_HEADER)
    file.file.seek(0)
    try:
        hasil = validasi_unggahan(file.filename, file.content_type, header)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe_name = f"{uuid.uuid4().hex}{hasil.ext}"
    dest_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    try:
        simpan_dengan_batas(
            file.file, dest_path, settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        if hasil.adalah_dokumen:
            chunk_count = index_document(db, dest_path, file.filename)
            return UploadResponse(
                filename=file.filename,
                status="processed",
                detail=f"{chunk_count} chunk berhasil diindeks ke knowledge base.",
            )

        # Gambar: disimpan dan dikembalikan sebagai image_id. Frontend mengirim id ini
        # pada POST /chat berikutnya, lalu agent menjalankan OCR di server.
        return UploadResponse(
            filename=file.filename,
            status="uploaded",
            detail="Gambar siap dibaca. Tulis pertanyaan tentang isi gambar ini.",
            image_id=safe_name,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(status_code=500, detail=f"Gagal memproses file: {exc}") from exc
