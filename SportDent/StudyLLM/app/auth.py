from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time


DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "StudyLLM2026"
DEFAULT_SESSION_TTL_SECONDS = 30 * 24 * 60 * 60


def _base64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class AuthManager:
    COOKIE_NAME = "sportdent_session"

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        secret: str | bytes | None = None,
        ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    ):
        self.username = username or os.environ.get("SPORTDENT_USERNAME", DEFAULT_USERNAME)
        self.password = password or os.environ.get("SPORTDENT_PASSWORD", DEFAULT_PASSWORD)
        configured_secret = secret or os.environ.get("SPORTDENT_SESSION_SECRET")
        self.secret = (
            configured_secret.encode("utf-8")
            if isinstance(configured_secret, str)
            else configured_secret or secrets.token_bytes(32)
        )
        self.ttl_seconds = ttl_seconds

    @property
    def uses_default_credentials(self) -> bool:
        return self.username == DEFAULT_USERNAME and self.password == DEFAULT_PASSWORD

    def authenticate(self, username: str, password: str) -> bool:
        return hmac.compare_digest(username, self.username) and hmac.compare_digest(password, self.password)

    def issue_token(self, *, now: int | None = None) -> str:
        issued_at = int(time.time() if now is None else now)
        payload = _base64_encode(
            json.dumps(
                {"username": self.username, "expires_at": issued_at + self.ttl_seconds},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        signature = _base64_encode(hmac.new(self.secret, payload.encode("ascii"), hashlib.sha256).digest())
        return f"{payload}.{signature}"

    def verify_token(self, token: str | None, *, now: int | None = None) -> bool:
        if not token:
            return False
        try:
            payload, received_signature = token.split(".", 1)
            expected_signature = _base64_encode(
                hmac.new(self.secret, payload.encode("ascii"), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(received_signature, expected_signature):
                return False
            data = json.loads(_base64_decode(payload))
            current_time = int(time.time() if now is None else now)
            return data["username"] == self.username and current_time < int(data["expires_at"])
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return False
