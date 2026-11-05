from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from kernel.models import BaseModel, TenantModel
from kernel.uuid7 import uuid7


class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class User(BaseModel):
    """A person across the platform. No tenant_id, no RLS: one person, many memberships.

    Created on first sight of a JWT (kernel.auth). email is nullable because guest tokens
    carry minimal claims (docs/backend.md, "Guest (no-account) booking").
    """

    auth_subject = models.TextField(unique=True)  # "<iss>|<sub>"
    email = models.EmailField(null=True, blank=True)
    full_name = models.TextField(default="")
    phone = models.TextField(null=True, blank=True)
    locale = models.TextField(null=True, blank=True)
    status = models.TextField(choices=UserStatus.choices, default=UserStatus.ACTIVE)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="users_email_ci_unique"),
        ]


class MembershipStatus(models.TextChoices):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class Membership(TenantModel):
    """This person belongs to this tenant. Also the customer profile inside the tenant."""

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="memberships")
    status = models.TextField(choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE)
    display_name = models.TextField(null=True, blank=True)
    default_location = models.ForeignKey(
        "resources.Location", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    invited_by = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_column="invited_by_membership_id",
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    attributes = models.JSONField(default=dict)
    schema = models.ForeignKey(
        "config.ObjectSchemaVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "memberships"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "user"], name="memberships_tenant_user"),
            models.UniqueConstraint(fields=["tenant", "id"], name="memberships_tenant_id"),
        ]


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.PROTECT, related_name="+", db_index=False
    )
    code = models.TextField()
    name = models.TextField()
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "roles"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "code"], name="roles_tenant_code"),
            models.UniqueConstraint(fields=["tenant", "id"], name="roles_tenant_id"),
        ]


class RolePermission(models.Model):
    """No tenant_id (follows its role). Readable only through roles, which RLS protects."""

    pk = models.CompositePrimaryKey("role_id", "permission")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    permission = models.TextField()

    class Meta:
        db_table = "role_permissions"


class MembershipRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.PROTECT, related_name="+", db_index=False
    )
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="+")
    location = models.ForeignKey(
        "resources.Location", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        db_table = "membership_roles"
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "role", "location"],
                name="membership_roles_unique",
                nulls_distinct=False,
            ),
        ]
