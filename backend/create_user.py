"""
create_user.py
Buat user awal (biasanya ADMIN pertama) dari command line.

Contoh:
    .venv/bin/python create_user.py admin --role ADMIN
    .venv/bin/python create_user.py tik --role USER --password rahasia
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from database import SessionLocal, init_db
from models import User
from security import ROLE_ADMIN, ROLE_READ_ONLY, ROLE_USER, hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Buat user baru.")
    parser.add_argument("username")
    parser.add_argument("--role", default=ROLE_USER, choices=[ROLE_READ_ONLY, ROLE_USER, ROLE_ADMIN])
    parser.add_argument("--password", help="Jika kosong, akan ditanyakan secara interaktif.")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    if not password:
        print("Password tidak boleh kosong.", file=sys.stderr)
        return 1

    init_db()
    db = SessionLocal()
    try:
        if db.execute(select(User).where(User.username == args.username)).scalar_one_or_none():
            print(f"User '{args.username}' sudah ada.", file=sys.stderr)
            return 1

        user = User(
            username=args.username,
            password_hash=hash_password(password),
            role=args.role,
        )
        db.add(user)
        db.commit()
        print(f"User '{args.username}' dibuat dengan role {args.role}.")
        return 0
    except ValueError as exc:
        print(f"Gagal: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
