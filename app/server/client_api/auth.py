import hashlib
import re
import secrets
import time
import threading
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import HTTPException

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY = hasher.hash(secrets.token_urlsafe(32))
_attempts = {}
_lock = threading.Lock()


def email_address(value):
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise HTTPException(422, "Enter a valid email address.")
    return value


def password_check(password, username="", email=""):
    if not 12 <= len(password) <= 128 or not all(
        (
            re.search(r"[a-z]", password),
            re.search(r"[A-Z]", password),
            re.search(r"[0-9]", password),
            re.search(r"[^a-zA-Z0-9\s]", password),
        )
    ):
        raise HTTPException(
            422,
            "Use 12–128 characters with uppercase, lowercase, a number and a symbol.",
        )
    if any(
        len(part) >= 4 and part.lower() in password.lower()
        for part in (username, email.split("@")[0])
    ):
        raise HTTPException(
            422, "Choose a password that does not include your name or email."
        )


def verify(password, hashed):
    try:
        return hasher.verify(hashed or DUMMY, password)
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def throttle(key):
    with _lock:
        now = time.time()
        for old in [k for k, v in _attempts.items() if not v or v[-1] < now - 600]:
            _attempts.pop(old, None)
        hits = [t for t in _attempts.get(key, []) if t > now - 600]
        if len(hits) >= 10:
            raise HTTPException(429, "Too many attempts. Please wait 10 minutes.")
        _attempts[key] = hits + [now]
