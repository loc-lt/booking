"""Signing JWTs that kernel.auth.AuthAdapter accepts.

sign() is used by modules/identity (login, refresh, guest tokens). mint() makes development
tokens for any subject and only runs with DEBUG on: real tokens come from logging in.
"""

import time
from typing import Any

import jwt
from django.conf import settings

from kernel.uuid7 import uuid7


class NotInDebug(RuntimeError):
    pass


def sign(sub: str, *, ttl_seconds: int, extra: dict[str, Any] | None = None) -> str:
    """An access token for `sub`, signed with JWT_SECRET (HS256)."""
    cfg = settings.JWT
    if not cfg["SECRET"]:
        raise RuntimeError("Issuing tokens needs JWT_SECRET.")
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": cfg["ISSUER"],
        "aud": cfg["AUDIENCE"],
        "sub": sub,
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": uuid7().hex,
        **(extra or {}),
    }
    return jwt.encode(claims, cfg["SECRET"], algorithm="HS256")


def mint(sub: str, *, email: str | None = None, name: str = "", hours: int = 12) -> str:
    if not settings.DEBUG:
        raise NotInDebug("Development tokens need DJANGO_DEBUG=true.")
    extra: dict[str, Any] = {}
    if email:
        # The demo auth service vouches for the address, so invitations can be accepted.
        extra.update(email=email, email_verified=True)
    if name:
        extra["name"] = name
    return sign(sub, ttl_seconds=hours * 3600, extra=extra)
