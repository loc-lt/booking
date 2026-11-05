"""Sign-in data (D-003): passwords, refresh tokens, one-time links.

Platform-wide like `users`: no tenant_id and no RLS. Only modules/identity/service.py writes
them. Secrets are never stored: passwords as Django PBKDF2 hashes, tokens as SHA-256.
"""

from django.db import models
from django.utils import timezone

from kernel.uuid7 import uuid7


class Credential(models.Model):
    """A user's password. Users without a row (guests, invited people) cannot log in."""

    user = models.OneToOneField(
        "users.User", on_delete=models.CASCADE, primary_key=True, related_name="credential"
    )
    password_hash = models.TextField()
    password_changed_at = models.DateTimeField(default=timezone.now)
    failed_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_credentials"


class RefreshToken(models.Model):
    """One refresh token. Using it rotates it (revoked, replaced by a new one of the same
    family); using a revoked one again revokes the whole family (token theft)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="+")
    family_id = models.UUIDField()
    token_hash = models.TextField(unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    replaced_by_id = models.UUIDField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "refresh_tokens"
        indexes = [models.Index(fields=["user", "family_id"], name="refresh_tokens_family")]


class LinkPurpose(models.TextChoices):
    PASSWORD_RESET = "password_reset"  # noqa: S105  (a link purpose, not a password)
    INVITATION = "invitation"


class OneTimeToken(models.Model):
    """The secret part of an emailed link (password reset, invitation). Single use."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    purpose = models.TextField(choices=LinkPurpose.choices)
    token_hash = models.TextField(unique=True)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="+")
    tenant_id = models.UUIDField(null=True, blank=True)
    membership_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_tokens"
        indexes = [models.Index(fields=["user", "purpose"], name="auth_tokens_user")]
