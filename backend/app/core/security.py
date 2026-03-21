import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import get_settings


class TokenError(ValueError):
    pass


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def _sign(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return _b64url_encode(digest)


def _hash_password(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return digest.hex()


def get_password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"{salt.hex()}${_hash_password(password, salt)}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt_hex, expected = hashed_password.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    observed = _hash_password(plain_password, salt)
    return hmac.compare_digest(expected, observed)


def create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = _sign(signing_input, settings.jwt_secret_key)
    return f"{header_b64}.{payload_b64}.{signature}"


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("Malformed token")

    header_b64, payload_b64, signature = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = _sign(signing_input, settings.jwt_secret_key)
    if not hmac.compare_digest(signature, expected_signature):
        raise TokenError("Invalid signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise TokenError("Invalid payload") from exc

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise TokenError("Missing exp")
    if exp < int(datetime.now(timezone.utc).timestamp()):
        raise TokenError("Token expired")

    return payload


def create_access_token(subject: str) -> str:
    settings = get_settings()
    return create_token(subject, timedelta(minutes=settings.access_token_expire_minutes), "access")


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    return create_token(subject, timedelta(minutes=settings.refresh_token_expire_minutes), "refresh")

