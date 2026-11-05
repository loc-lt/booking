"""Public interface of the identity module: signing in to the booking core (D-003).

The rest of the core does not change: every endpoint still only verifies a JWT
(kernel.auth.AuthAdapter). This module is what issues them:

  register / login / invitation link  -> access token (short) + refresh token (rotating)
  refresh                             -> new pair; reusing an old refresh token revokes its family
  guest                               -> access token only, a few hours, guest role in one tenant
  forgot / reset / change password    -> one-time emailed link; every refresh token revoked

Passwords: Django's PBKDF2 hasher, Django's password validators. Accounts lock for a while
after repeated wrong passwords. Unknown email and wrong password get the same answer.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import get_password_validators, validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from kernel.devtokens import sign
from kernel.errors import Forbidden, NotFound, Unauthenticated, ValidationFailed
from kernel.tenant_context import activate_tenant
from kernel.uuid7 import uuid7
from modules.identity.models import Credential, LinkPurpose, OneTimeToken, RefreshToken
from modules.tenancy import service as tenancy
from modules.users import service as users

WRONG_LOGIN = "Wrong email or password."
# A real hash, so an unknown email costs the same time as a wrong password.
_DUMMY_HASH = make_password("not-a-real-password-just-for-timing")


def _cfg() -> dict[str, Any]:
    return settings.AUTH


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _check_password_rules(password: str, field: str = "password") -> None:
    try:
        validate_password(
            password, password_validators=get_password_validators(settings.PASSWORD_VALIDATORS)
        )
    except DjangoValidationError as exc:
        raise ValidationFailed([{"field": field, "message": m} for m in exc.messages]) from None


@dataclass(frozen=True, slots=True)
class Tokens:
    access_token: str
    expires_in: int
    refresh_token: str | None
    user: Any

    def json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "accessToken": self.access_token,
            "tokenType": "Bearer",
            "expiresIn": self.expires_in,
            "user": {
                "id": str(self.user.id),
                "email": self.user.email,
                "fullName": self.user.full_name or None,
            },
        }
        if self.refresh_token:
            out["refreshToken"] = self.refresh_token
        return out


def _access(user: Any, ttl: int) -> str:
    sub = users.local_subject(user)
    if sub is None:
        raise Unauthenticated("This account signs in elsewhere.")
    extra: dict[str, Any] = {}
    if user.email:
        extra.update(email=user.email, email_verified=False)
    if user.full_name:
        extra["name"] = user.full_name
    return sign(sub, ttl_seconds=ttl, extra=extra)


def _new_refresh(user: Any, family_id: UUID, user_agent: str | None) -> tuple[RefreshToken, str]:
    raw = secrets.token_urlsafe(32)
    row = RefreshToken.objects.create(
        user=user,
        family_id=family_id,
        token_hash=_hash(raw),
        expires_at=timezone.now() + timedelta(days=_cfg()["REFRESH_TTL_DAYS"]),
        user_agent=(user_agent or "")[:300] or None,
    )
    return row, raw


def _pair(user: Any, *, user_agent: str | None, family_id: UUID | None = None) -> Tokens:
    ttl = _cfg()["ACCESS_TTL_SECONDS"]
    _, raw = _new_refresh(user, family_id or uuid7(), user_agent)
    return Tokens(access_token=_access(user, ttl), expires_in=ttl, refresh_token=raw, user=user)


def _set_password(user: Any, password: str) -> None:
    Credential.objects.update_or_create(
        user=user,
        defaults={
            "password_hash": make_password(password),
            "password_changed_at": timezone.now(),
            "failed_attempts": 0,
            "locked_until": None,
        },
    )


def set_password(user: Any, password: str) -> None:
    """For platform commands (seed_demo): give an existing user a password."""
    _check_password_rules(password)
    _set_password(user, password)


def _revoke_all(user_id: UUID) -> None:
    RefreshToken.objects.filter(user_id=user_id, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )


# ---------- accounts ----------


@transaction.atomic
def register(*, email: str, password: str, full_name: str, user_agent: str | None) -> Tokens:
    existing = users.find_user_by_email(email)
    if existing is not None:
        message = (
            "This email has a pending invitation: use the link in the invitation email."
            if users.is_placeholder(existing)
            else "An account with this email already exists."
        )
        raise ValidationFailed.one("email", message)
    _check_password_rules(password)
    user = users.create_user(email=email, full_name=full_name)
    _set_password(user, password)
    users.record_login(user)
    return _pair(user, user_agent=user_agent)


def login(*, email: str, password: str, user_agent: str | None) -> Tokens:
    """Not one transaction on purpose: a wrong password must still be counted (and the
    account locked) even though the request fails. Views call it outside ATOMIC_REQUESTS."""
    with transaction.atomic():
        user = users.find_user_by_email(email)
        credential = (
            Credential.objects.select_for_update().filter(user=user).first() if user else None
        )
        if credential is None:
            check_password(password, _DUMMY_HASH)
            failure = WRONG_LOGIN
        elif credential.locked_until and credential.locked_until > timezone.now():
            failure = "Too many wrong passwords. Try again later or reset your password."
        elif not check_password(password, credential.password_hash):
            credential.failed_attempts += 1
            if credential.failed_attempts >= _cfg()["MAX_FAILED_LOGINS"]:
                credential.locked_until = timezone.now() + timedelta(minutes=_cfg()["LOCK_MINUTES"])
                credential.failed_attempts = 0
            credential.save(update_fields=["failed_attempts", "locked_until"])
            failure = WRONG_LOGIN
        elif user.status != "ACTIVE":
            failure = "This account is disabled."
        else:
            credential.failed_attempts = 0
            credential.locked_until = None
            credential.save(update_fields=["failed_attempts", "locked_until"])
            users.record_login(user)
            return _pair(user, user_agent=user_agent)
    raise Unauthenticated(failure)  # after the counter is committed


def refresh(*, refresh_token: str, user_agent: str | None) -> Tokens:
    """Rotate a refresh token. Reusing an already used one revokes its whole family (it has
    probably leaked); that revocation is committed before the 401 is returned."""
    with transaction.atomic():
        row = (
            RefreshToken.objects.select_for_update().filter(token_hash=_hash(refresh_token)).first()
        )
        now = timezone.now()
        if row is None or row.expires_at <= now:
            failure = "Sign in again."
        elif row.revoked_at is not None:
            RefreshToken.objects.filter(family_id=row.family_id, revoked_at__isnull=True).update(
                revoked_at=now
            )
            failure = "Sign in again."
        else:
            user = users.get_user(row.user_id)
            if user.status != "ACTIVE":
                failure = "This account is disabled."
            else:
                tokens = _pair(user, user_agent=user_agent, family_id=row.family_id)
                new = RefreshToken.objects.get(token_hash=_hash(tokens.refresh_token or ""))
                row.revoked_at = now
                row.replaced_by_id = new.id
                row.save(update_fields=["revoked_at", "replaced_by_id"])
                return tokens
    raise Unauthenticated(failure)


@transaction.atomic
def logout(*, refresh_token: str) -> None:
    row = RefreshToken.objects.filter(token_hash=_hash(refresh_token)).first()
    if row is not None:
        RefreshToken.objects.filter(family_id=row.family_id, revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )


@transaction.atomic
def change_password(*, user_id: UUID, current: str, new: str, user_agent: str | None) -> Tokens:
    credential = Credential.objects.select_for_update().filter(user_id=user_id).first()
    if credential is None or not check_password(current, credential.password_hash):
        raise ValidationFailed.one("currentPassword", "Wrong password.")
    _check_password_rules(new, "newPassword")
    user = users.get_user(user_id)
    _set_password(user, new)
    _revoke_all(user_id)  # every other device signs in again
    return _pair(user, user_agent=user_agent)


# ---------- emailed links ----------


def issue_link(
    *,
    purpose: str,
    user: Any,
    ttl: timedelta,
    tenant_id: UUID | None = None,
    membership_id: UUID | None = None,
) -> str:
    """Create a one-time token and return the full link. Only its hash is stored."""
    raw = secrets.token_urlsafe(32)
    OneTimeToken.objects.create(
        purpose=purpose,
        token_hash=_hash(raw),
        user=user,
        tenant_id=tenant_id,
        membership_id=membership_id,
        expires_at=timezone.now() + ttl,
    )
    page = "accept-invitation" if purpose == LinkPurpose.INVITATION else "reset-password"
    return f"{_cfg()['APP_URL'].rstrip('/')}/{page}?token={raw}"


def _email(to: str, subject: str, body: str) -> None:
    # After commit: never send mail from inside the transaction (API_KICH_BAN.md 1).
    transaction.on_commit(lambda: send_mail(subject, body, None, [to], fail_silently=False))


@transaction.atomic
def forgot_password(*, email: str) -> None:
    """Always the same answer, whether or not the email has an account."""
    user = users.find_user_by_email(email)
    if user is None or not Credential.objects.filter(user=user).exists():
        return
    link = issue_link(
        purpose=LinkPurpose.PASSWORD_RESET,
        user=user,
        ttl=timedelta(seconds=_cfg()["RESET_TTL_SECONDS"]),
    )
    _email(
        user.email,
        "Đặt lại mật khẩu",
        f"Mở link sau để đặt mật khẩu mới (dùng một lần):\n\n{link}\n",
    )


def _use_link(raw: str, purpose: str) -> OneTimeToken:
    row = (
        OneTimeToken.objects.select_for_update()
        .filter(token_hash=_hash(raw), purpose=purpose)
        .first()
    )
    if row is None or row.used_at is not None or row.expires_at <= timezone.now():
        raise ValidationFailed.one("token", "This link is invalid or has expired.")
    row.used_at = timezone.now()
    row.save(update_fields=["used_at"])
    return row


@transaction.atomic
def reset_password(*, token: str, password: str, user_agent: str | None) -> Tokens:
    row = _use_link(token, LinkPurpose.PASSWORD_RESET)
    _check_password_rules(password)
    user = users.get_user(row.user_id)
    _set_password(user, password)
    _revoke_all(user.id)
    return _pair(user, user_agent=user_agent)


def send_invitation(*, tenant_id: UUID, membership_id: UUID, email: str, tenant_name: str) -> str:
    """Called by the worker for member.invited (consumers.py): the link exists only here and
    in the email, never in the outbox."""
    user = users.find_user_by_email(email)
    if user is None:
        raise NotFound("No user with this email.")
    link = issue_link(
        purpose=LinkPurpose.INVITATION,
        user=user,
        ttl=timedelta(days=_cfg()["INVITATION_TTL_DAYS"]),
        tenant_id=tenant_id,
        membership_id=membership_id,
    )
    _email(
        email,
        f"Lời mời tham gia {tenant_name}",
        f"Bạn được mời tham gia {tenant_name}.\n\nNhận lời mời:\n{link}\n",
    )
    return link


@transaction.atomic
def accept_invitation(
    *, token: str, password: str | None, full_name: str | None, user_agent: str | None
) -> tuple[Tokens, UUID]:
    """The invitation link: set a password (new person) or confirm it (existing account),
    then the membership becomes ACTIVE."""
    row = _use_link(token, LinkPurpose.INVITATION)
    user = users.get_user(row.user_id)
    credential = Credential.objects.filter(user=user).first()
    if credential is not None:
        if not password or not check_password(password, credential.password_hash):
            raise ValidationFailed.one("password", "Enter the password of your existing account.")
    else:
        if not password:
            raise ValidationFailed.one("password", "Choose a password.")
        _check_password_rules(password)
        users.claim_placeholder(user, full_name=full_name)
        _set_password(user, password)
    activate_tenant(row.tenant_id)
    users.accept_invitation(user_id=user.id, tenant_id=row.tenant_id)
    activate_tenant(None)
    users.record_login(user)
    return _pair(user, user_agent=user_agent), row.tenant_id


# ---------- guests ----------


@transaction.atomic
def guest(
    *, tenant_id: UUID, name: str, email: str | None, phone: str | None
) -> tuple[Tokens, UUID]:
    """Booking without an account (docs/backend.md, "Guest booking"): an access token of a few
    hours, no refresh token, the guest role in this tenant only."""
    try:
        tenant = tenancy.get_tenant(tenant_id)
    except Exception:
        raise NotFound("Unknown tenant.") from None
    if tenant.status != "ACTIVE" or not tenant.settings.get("guestBooking", True):
        raise Forbidden("This tenant does not take guest bookings.")
    activate_tenant(tenant.id)
    membership = users.add_guest(tenant_id=tenant.id, name=name, email=email, phone=phone)
    activate_tenant(None)
    user = users.get_user(membership.user_id)
    ttl = _cfg()["GUEST_TTL_SECONDS"]
    return Tokens(
        access_token=_access(user, ttl), expires_in=ttl, refresh_token=None, user=user
    ), membership.id


def tenants_of(user_id: UUID) -> list[dict[str, Any]]:
    return users.memberships_of_user(user_id)
