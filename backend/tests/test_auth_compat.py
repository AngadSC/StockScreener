"""Backward compatibility after replacing python-jose -> PyJWT and passlib -> bcrypt.

The fixtures below were produced by the OLD stack (passlib 1.7.4 CryptContext
bcrypt + python-jose 3.3.0 HS256) and pasted in verbatim. If these stop
verifying, every existing user is logged out or locked out on deploy.
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://u:p@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from datetime import timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from app.config import settings  # noqa: E402
from app.services import auth  # noqa: E402

# passlib CryptContext(schemes=["bcrypt"]).hash("correct horse battery staple")
LEGACY_HASH = "$2b$12$vQYsAIKaWRqNNx7O80uL4ukLhChV5mjXRRsgck7KQz3MOc0NmRHxW"
# passlib hash of "p" * 100 -- passlib silently truncated to bcrypt's 72 bytes
LEGACY_LONG_HASH = "$2b$12$5ZCMUbFxcPTWH9vXaPuM1esivpj./UhlNr5NqLgKxtnf6ToZTOSs."
# jose.jwt.encode({"sub": "legacy@example.com", "exp": datetime(2099, 1, 1)},
#                 "legacy-test-secret-0123456789abcdef", algorithm="HS256")
LEGACY_SECRET = "legacy-test-secret-0123456789abcdef"
LEGACY_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJsZWdhY3lAZXhhbXBsZS5jb20iLCJleHAiOjQwNzA5MDg4MDB9."
    "SJC_7tM2bu9hCe4SNvD0t8CfKNxPPrGSNnxglSDyDok"
)


class _FakeDB:
    """Just enough of a Session for get_current_user's single lookup."""

    def __init__(self, user):
        self.user = user

    def query(self, _model):
        return self

    def filter(self, *_args):
        return self

    def first(self):
        return self.user


def test_legacy_passlib_hash_still_verifies():
    assert auth.verify_password("correct horse battery staple", LEGACY_HASH)
    assert not auth.verify_password("wrong password", LEGACY_HASH)


def test_legacy_long_password_hash_still_verifies():
    assert auth.verify_password("p" * 100, LEGACY_LONG_HASH)


def test_new_hash_round_trip_and_format():
    hashed = auth.get_password_hash("hunter2hunter2")
    assert hashed.startswith("$2b$12$")
    assert auth.verify_password("hunter2hunter2", hashed)
    assert not auth.verify_password("nope", hashed)
    assert not auth.verify_password("x", "not-a-bcrypt-hash")
    assert not auth.verify_password("x", "")


def test_legacy_jose_token_still_authenticates(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", LEGACY_SECRET)
    user = object()
    assert auth.get_current_user(LEGACY_TOKEN, _FakeDB(user)) is user


def test_new_token_round_trip(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", LEGACY_SECRET)
    token = auth.create_access_token({"sub": "a@b.com"}, timedelta(minutes=5))
    user = object()
    assert auth.get_current_user(token, _FakeDB(user)) is user


@pytest.mark.parametrize(
    "token",
    [
        LEGACY_TOKEN[:-2] + "xx",  # bad signature
        "garbage",
    ],
)
def test_bad_tokens_rejected(monkeypatch, token):
    monkeypatch.setattr(settings, "SECRET_KEY", LEGACY_SECRET)
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(token, _FakeDB(object()))
    assert exc.value.status_code == 401


def test_expired_and_wrong_secret_rejected(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", LEGACY_SECRET)
    expired = auth.create_access_token({"sub": "a@b.com"}, timedelta(minutes=-1))
    with pytest.raises(HTTPException):
        auth.get_current_user(expired, _FakeDB(object()))
    monkeypatch.setattr(settings, "SECRET_KEY", "some-other-secret-0123456789abcdef")
    with pytest.raises(HTTPException):
        auth.get_current_user(LEGACY_TOKEN, _FakeDB(object()))
