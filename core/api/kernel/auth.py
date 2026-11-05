"""Token verification (docs/backend.md, "Auth").

Every request carries a JWT, guests included. Since D-003 the core issues them itself
(modules/identity: sign-in, refresh, invitation links, guest tokens); locally, dev tokens too.
This module only verifies. AuthAdapter is the one place that knows how tokens are checked, so
moving to RS256/JWKS or an outside provider touches one class.
"""

from dataclasses import dataclass
from functools import cache
from typing import Any

import jwt
from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.request import Request

from kernel.errors import Unauthenticated
from kernel.tenant_context import activate_user


@dataclass(frozen=True, slots=True)
class Principal:
    """The signed-in person, mapped to a core user. DRF puts it on request.user."""

    user_id: Any
    subject: str
    claims: dict[str, Any]

    @property
    def is_authenticated(self) -> bool:
        return True


class AuthAdapter:
    def __init__(self) -> None:
        cfg = settings.JWT
        self.issuer = cfg["ISSUER"]
        self.audience = cfg["AUDIENCE"]
        self.algorithms = cfg["ALGORITHMS"]
        self.leeway = cfg["LEEWAY_SECONDS"]
        self.jwks = jwt.PyJWKClient(cfg["JWKS_URL"]) if cfg["JWKS_URL"] else None
        self.secret = cfg["SECRET"]
        if not self.jwks and not self.secret:
            raise RuntimeError("Set JWT_JWKS_URL or JWT_SECRET.")

    def verify(self, token: str) -> dict[str, Any]:
        """Signature, exp, iss and aud are always checked. Raises Unauthenticated."""
        try:
            key: Any = self.jwks.get_signing_key_from_jwt(token).key if self.jwks else self.secret
            return jwt.decode(
                token,
                key=key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.leeway,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError:
            raise Unauthenticated("Token expired.") from None
        except jwt.PyJWTError:
            raise Unauthenticated("Invalid token.") from None


@cache
def get_adapter() -> AuthAdapter:
    return AuthAdapter()


def _user_resolver() -> Any:
    # Resolved by path so the kernel does not import the users module.
    return import_string("modules.users.service.user_from_claims")


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request: Request) -> tuple[Principal, str] | None:
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != b"bearer":
            return None
        if len(header) != 2:
            raise Unauthenticated("Malformed Authorization header.")
        token = header[1].decode()
        claims = get_adapter().verify(token)
        user_id = _user_resolver()(claims)
        activate_user(user_id)
        return Principal(user_id=user_id, subject=claims["sub"], claims=claims), token

    def authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="api"'
