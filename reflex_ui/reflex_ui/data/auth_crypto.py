from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any

import bcrypt


def jwt_secret() -> str:
    secret = os.environ.get("AUTH_JWT_SECRET", "").strip()
    if not secret:
        secret = "dev-only-insecure-secret-change-in-production"
    return secret


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _sign_hs256(signing_input: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return _b64url_encode(sig)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"), password_hash.encode("ascii")
        )
    except (ValueError, TypeError):
        return False


def issue_user_token(user_id: uuid.UUID, *, ttl_days: int = 7) -> str:
    header: dict[str, str] = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + ttl_days * 86400,
    }
    header_b = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b}.{payload_b}".encode("ascii")
    signature = _sign_hs256(signing_input, jwt_secret())
    return f"{header_b}.{payload_b}.{signature}"


def verify_user_token(token: str | None) -> uuid.UUID | None:
    if not token or not token.strip():
        return None
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None
    header_b, payload_b, signature = parts
    signing_input = f"{header_b}.{payload_b}".encode("ascii")
    expected = _sign_hs256(signing_input, jwt_secret())
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b).decode("utf-8"))
        exp = int(payload.get("exp", 0))
        if exp <= int(time.time()):
            return None
        return uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        return None
