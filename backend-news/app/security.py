import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import delete, func, update
from sqlalchemy.orm import Session

from . import models
from .database import get_db


load_dotenv(Path(__file__).resolve().parent.parent / ".env")
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_urlsafe(48)
SESSION_COOKIE = "newshub_session"
SESSION_TTL_SECONDS = 60 * 60 * 12
PASSWORD_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode().rstrip("="),
        base64.urlsafe_b64encode(digest).decode().rstrip("="),
    )


def verify_password(password: str, stored_password: str) -> tuple[bool, bool]:
    """Return (valid, needs_upgrade), supporting legacy plaintext passwords once."""
    if not stored_password.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(password.encode(), stored_password.encode()), True

    try:
        _, iterations, salt_text, digest_text = stored_password.split("$", 3)
        iterations = int(iterations)
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(digest_text + "=" * (-len(digest_text) % 4))
    except (ValueError, TypeError, binascii.Error):
        return False, False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(actual, expected), iterations < PASSWORD_ITERATIONS


def _captcha_digest(challenge_id: str, answer: str) -> str:
    return hashlib.sha256(f"captcha:{challenge_id}:{answer.strip().upper()}".encode()).hexdigest()


def create_captcha(db: Session) -> dict[str, str]:
    """Create a short-lived server-verified image CAPTCHA challenge."""
    db.execute(delete(models.CaptchaChallenge).where(models.CaptchaChallenge.expires_at < func.now()))
    challenge_id = secrets.token_urlsafe(24)
    answer = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(5))
    db.add(models.CaptchaChallenge(
        id=challenge_id,
        answer_hash=_captcha_digest(challenge_id, answer),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        consumed=0,
    ))
    db.commit()

    glyphs = {
        "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
        "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
        "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
        "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
        "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
        "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
        "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
        "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
        "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
        "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
        "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
        "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
        "N": ("10001", "11001", "11001", "10101", "10011", "10011", "10001"),
        "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
        "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
        "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
        "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
        "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
        "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
        "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
        "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
        "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
        "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
        "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
        "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
        "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
        "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
        "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
        "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
        "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
        "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
        "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    }
    glyph_parts = []
    for index, char in enumerate(answer):
        rotate = secrets.randbelow(31) - 15
        x, y = 8 + index * 31, 15 + secrets.randbelow(7)
        pixels = "".join(
            f'<rect x="{x + column * 3}" y="{y + row * 3}" width="2.4" height="2.4" rx=".4"/>'
            for row, pattern in enumerate(glyphs[char])
            for column, pixel in enumerate(pattern)
            if pixel == "1"
        )
        glyph_parts.append(f'<g transform="rotate({rotate} {x + 7} {y + 10})">{pixels}</g>')
    lines = "".join(
        f'<path d="M{secrets.randbelow(180)} {secrets.randbelow(54)} '
        f'L{secrets.randbelow(180)} {secrets.randbelow(54)}" />'
        for _ in range(6)
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="170" height="58" viewBox="0 0 170 58">'
        '<rect width="170" height="58" rx="8" fill="#eef2ff"/>'
        f'<g stroke="#818cf8" stroke-width="1.5" opacity=".65">{lines}</g>'
        f'<g fill="#1e293b">{"".join(glyph_parts)}</g>'
        '</svg>'
    )
    image = base64.b64encode(svg.encode()).decode()
    return {"id": challenge_id, "image": f"data:image/svg+xml;base64,{image}"}


def consume_captcha(db: Session, challenge_id: str, answer: str) -> bool:
    if not challenge_id or not answer:
        return False
    challenge = db.query(models.CaptchaChallenge).filter(
        models.CaptchaChallenge.id == challenge_id,
    ).first()
    if not challenge:
        return False
    expected = challenge.answer_hash
    result = db.execute(
        update(models.CaptchaChallenge)
        .where(
            models.CaptchaChallenge.id == challenge_id,
            models.CaptchaChallenge.consumed == 0,
            models.CaptchaChallenge.expires_at > func.now(),
        )
        .values(consumed=1)
    )
    db.commit()
    supplied = _captcha_digest(challenge_id, answer)
    return result.rowcount == 1 and hmac.compare_digest(expected, supplied)


def issue_session_token(user: models.User) -> str:
    payload = {
        "sub": user.id,
        "role": user.role,
        "exp": int(time.time()) + SESSION_TTL_SECONDS,
    }
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    signature_text = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{body}.{signature_text}"


def decode_session_token(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None
    body, signature_text = token.split(".", 1)
    expected = hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    try:
        signature = base64.urlsafe_b64decode(signature_text + "=" * (-len(signature_text) % 4))
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except (ValueError, TypeError, binascii.Error, json.JSONDecodeError):
        return None
    if not hmac.compare_digest(signature, expected):
        return None
    if not isinstance(payload, dict) or payload.get("exp", 0) < int(time.time()):
        return None
    if payload.get("role") not in {"admin", "writer"}:
        return None
    return payload


def set_session_cookie(response, user: models.User) -> str:
    token = issue_session_token(user)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
    )
    return token


def clear_session_cookie(response):
    response.delete_cookie(SESSION_COOKIE, path="/")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> models.User:
    token = request.cookies.get(SESSION_COOKIE)
    if authorization:
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() == "bearer" and credentials:
            token = credentials
    payload = decode_session_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Silakan login terlebih dahulu.")

    user = db.query(models.User).filter(models.User.id == payload["sub"]).first()
    if not user or user.role != payload["role"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesi tidak valid. Silakan login kembali.")
    return user


def require_role(role: str):
    def dependency(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Anda tidak memiliki akses untuk tindakan ini.")
        return user
    return dependency


require_admin = require_role("admin")
require_writer = require_role("writer")
