from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from threading import Lock
from urllib.parse import urlparse

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _password_hasher.check_needs_rehash(password_hash)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def verify_origin_header(
    origin: str | None,
    referer: str | None,
    allowed_origins: list[str],
    request_host: str | None,
) -> bool:
    """Protect cookie-authenticated state-changing endpoints against CSRF."""
    candidate = origin or referer
    if not candidate:
        # Non-browser or same-origin tools without Origin header: allow only if Origin/Referer not spoofed;
        # browsers always send Origin or Referer on cross-site POST/PUT/PATCH/DELETE.
        return True
    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        return False
    normalized = f"{parsed.scheme}://{parsed.netloc}".rstrip("/").lower()
    if request_host and parsed.netloc.lower() == request_host.lower():
        return True
    return any(normalized == allowed.lower() for allowed in allowed_origins)


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


class InMemoryRateLimiter:
    """Thread-safe sliding-window rate limiter per key."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, max_requests: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            q = self._hits[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= max_requests:
                retry_after = max(1, int(q[0] + window_seconds - now))
                return False, retry_after
            q.append(now)
            return True, 0


rate_limiter = InMemoryRateLimiter()
