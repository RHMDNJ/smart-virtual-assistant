"""
schemas.py
Pydantic schema untuk request & response FastAPI, sesuai kontrak API di README (bagian 20).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str
    # ID gambar hasil POST /upload (bukan path absolut, agar tidak bisa dipakai
    # untuk membaca file sembarangan di server).
    image_id: Optional[str] = None
    # Nama dokumen yang baru diunggah pada giliran ini. Bila diisi, pencarian
    # dibatasi pada dokumen itu.
    document_filename: Optional[str] = None


class SourceItem(BaseModel):
    filename: str


class ChatResponse(BaseModel):
    answer: str
    tool_used: str
    sources: list[SourceItem] = []


class ChatHistoryItem(BaseModel):
    id: int
    session_id: str
    role: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    filename: str
    status: str
    detail: Optional[str] = None
    # Terisi hanya untuk gambar: dikirim kembali oleh frontend pada POST /chat
    # sebagai `image_id` supaya agent bisa menjalankan OCR.
    image_id: Optional[str] = None


class DocumentRequest(BaseModel):
    filename: str
    content: str


class DocumentResponse(BaseModel):
    filename: str
    status: str
    chunks: int


class DocumentSummary(BaseModel):
    filename: str
    chunks: int
    characters: int
    created_at: datetime


class DocumentDetail(BaseModel):
    filename: str
    content: str
    chunks: int


class DocumentUpdateRequest(BaseModel):
    content: str


class ReindexResponse(BaseModel):
    reindexed: int
    skipped: int = 0
    total: int = 0


class HealthResponse(BaseModel):
    status: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "USER"
