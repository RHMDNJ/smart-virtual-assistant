"""
security.py
Authentication & Authorization (Bagian 18) — JWT + role-based access control.

Catatan implementasi: memakai pustaka `bcrypt` secara langsung, bukan `passlib`.
passlib 1.7.4 (rilis terakhir 2020) tidak kompatibel dengan bcrypt 5.x dan
melempar ValueError saat verifikasi.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User

# Role, dari yang paling terbatas ke paling luas (Bagian 18).
ROLE_READ_ONLY = "READ_ONLY"
ROLE_USER = "USER"
ROLE_ADMIN = "ADMIN"

_ROLE_RANK = {ROLE_READ_ONLY: 0, ROLE_USER: 1, ROLE_ADMIN: 2}

# bcrypt hanya memakai 72 byte pertama; tolak lebih panjang daripada memotong diam-diam.
MAX_PASSWORD_BYTES = 72

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password maksimal {MAX_PASSWORD_BYTES} byte.")
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None or not user.is_active:
        # Tetap jalankan verifikasi dummy agar waktu respons tidak membocorkan
        # apakah username tersebut ada.
        verify_password(password, bcrypt.hashpw(b"dummy", bcrypt.gensalt()).decode())
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    kredensial_invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kedaluwarsa.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        username = payload.get("sub")
        if not username:
            raise kredensial_invalid
    except JWTError:
        raise kredensial_invalid

    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None or not user.is_active:
        raise kredensial_invalid
    return user


def require_role(minimal: str):
    """
    Dependency factory: pastikan user punya role minimal tertentu.

    READ_ONLY < USER < ADMIN. Contoh: require_role(ROLE_USER) menolak READ_ONLY
    tetapi menerima USER dan ADMIN.
    """
    batas = _ROLE_RANK[minimal]

    def checker(user: User = Depends(get_current_user)) -> User:
        if _ROLE_RANK.get(user.role, -1) < batas:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Akses ditolak. Dibutuhkan role minimal {minimal}, role Anda {user.role}.",
            )
        return user

    return checker
