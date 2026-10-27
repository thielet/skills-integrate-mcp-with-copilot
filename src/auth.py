"""Teacher credentials and short-lived browser sessions."""

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Cookie, Depends, HTTPException

PASSWORD_HASH_ITERATIONS = 600_000
SESSION_DURATION_SECONDS = 8 * 60 * 60
COOKIE_NAME = "teacher_session"
TEACHERS_FILE = Path(
    os.environ.get("TEACHERS_FILE", Path(__file__).with_name("teachers.json"))
)
sessions: dict[str, tuple[str, float]] = {}


def make_password_record(username: str, password: str) -> dict[str, str]:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return {
        "username": username,
        "salt": salt.hex(),
        "password_hash": password_hash.hex(),
    }


def load_teachers() -> dict[str, dict[str, str]]:
    try:
        records = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}

    if not isinstance(records, list):
        raise ValueError("Teacher credentials must be a JSON list")

    teachers = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        username = record.get("username")
        salt = record.get("salt")
        password_hash = record.get("password_hash")
        if all(isinstance(value, str) and value for value in (username, salt, password_hash)):
            teachers[username] = record
    return teachers


def authenticate_teacher(username: str, password: str) -> bool:
    record = load_teachers().get(username)
    salt = b"invalid-user-salt"
    expected_hash = bytes(32)

    if record is not None:
        try:
            salt = bytes.fromhex(record["salt"])
            expected_hash = bytes.fromhex(record["password_hash"])
        except ValueError:
            return False

    supplied_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return record is not None and hmac.compare_digest(supplied_hash, expected_hash)


def create_session(username: str) -> str:
    now = time.time()
    expired_tokens = [
        token for token, (_, expires_at) in sessions.items() if expires_at <= now
    ]
    for token in expired_tokens:
        sessions.pop(token, None)

    session_token = secrets.token_urlsafe(32)
    sessions[session_token] = (username, now + SESSION_DURATION_SECONDS)
    return session_token


def revoke_session(session_token: str | None) -> None:
    if session_token:
        sessions.pop(session_token, None)


def get_optional_teacher(
    session_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> str | None:
    if not session_token:
        return None

    session = sessions.get(session_token)
    if session is None:
        return None

    username, expires_at = session
    if expires_at <= time.time() or username not in load_teachers():
        revoke_session(session_token)
        return None

    return username


def require_teacher(
    teacher_username: str | None = Depends(get_optional_teacher),
) -> str:
    if teacher_username is None:
        raise HTTPException(status_code=401, detail="Teacher login required")
    return teacher_username