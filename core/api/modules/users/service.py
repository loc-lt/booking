"""Public interface of the users module: identity mapping, memberships, roles, access."""

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from kernel.access import Access
from kernel.errors import Forbidden, InvalidTransition, NotFound, ValidationFailed
from kernel.history import record_status
from kernel.permissions import ALL_PERMISSIONS
from kernel.uuid7 import uuid7
from modules.events import service as events
from modules.resources import service as resources
from modules.users.constants import SYSTEM_ROLES
from modules.users.models import (
    Membership,
    MembershipRole,
    MembershipStatus,
    Role,
    RolePermission,
    User,
)

INVITE_PREFIX = "invite|"
ROLE_CODE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


# ---------- identity ----------


def _claim_invitation(subject: str, claims: dict[str, Any]) -> UUID | None:
    """A person invited by email signs in for the first time: give the placeholder user the
    real subject. Only with a verified email, or anyone could claim an invitation."""
    email = claims.get("email")
    if not email or claims.get("email_verified") is not True:
        return None
    updated = User.objects.filter(
        email__iexact=email, auth_subject__startswith=INVITE_PREFIX
    ).first()
    if updated is None:
        return None
    updated.auth_subject = subject
    updated.full_name = updated.full_name or claims.get("name") or ""
    updated.last_login_at = timezone.now()
    updated.save(update_fields=["auth_subject", "full_name", "last_login_at", "updated_at"])
    return updated.id


def user_from_claims(claims: dict[str, Any]) -> UUID:
    """Map a verified JWT to a core user id, creating the user on first sight."""
    subject = f"{claims['iss']}|{claims['sub']}"
    found = User.objects.filter(auth_subject=subject).values_list("id", flat=True).first()
    if found:
        return found
    claimed = _claim_invitation(subject, claims)
    if claimed:
        return claimed
    try:
        with transaction.atomic():
            user = User.objects.create(
                auth_subject=subject,
                email=claims.get("email") or None,
                full_name=claims.get("name") or "",
                locale=claims.get("locale"),
                last_login_at=timezone.now(),
            )
            return user.id
    except IntegrityError:
        pass
    # Either a parallel first request created it, or the email belongs to another subject
    # (then the new user is stored without email rather than failing the request).
    found = User.objects.filter(auth_subject=subject).values_list("id", flat=True).first()
    if found:
        return found
    return User.objects.create(
        auth_subject=subject, email=None, full_name=claims.get("name") or ""
    ).id


def get_or_create_user(*, issuer: str, subject: str, email: str | None, name: str = "") -> User:
    user, _ = User.objects.get_or_create(
        auth_subject=f"{issuer}|{subject}", defaults={"email": email, "full_name": name}
    )
    return user


def local_subject(user: User) -> str | None:
    """The `sub` this core puts in tokens for `user`: its auth_subject minus our issuer, or
    None when the user belongs to another issuer or is an invitation placeholder."""
    prefix = f"{settings.JWT['ISSUER']}|"
    return user.auth_subject[len(prefix) :] if user.auth_subject.startswith(prefix) else None


def get_user(user_id: UUID) -> User:
    return User.objects.get(id=user_id)


def find_user_by_email(email: str) -> User | None:
    return User.objects.filter(email__iexact=email.strip()).first()


def is_placeholder(user: User) -> bool:
    return user.auth_subject.startswith(INVITE_PREFIX)


def create_user(*, email: str | None, full_name: str, phone: str | None = None) -> User:
    """A user signed in by this core: sub = the user's own id."""
    user_id = uuid7()
    return User.objects.create(
        id=user_id,
        auth_subject=f"{settings.JWT['ISSUER']}|{user_id}",
        email=email.strip().lower() if email else None,
        full_name=full_name,
        phone=phone,
    )


def claim_placeholder(user: User, *, full_name: str | None) -> User:
    """An invited person sets a password through the emailed link: the placeholder user
    becomes a normal one signed in by this core."""
    if is_placeholder(user):
        user.auth_subject = f"{settings.JWT['ISSUER']}|{user.id}"
    if full_name:
        user.full_name = full_name
    user.save(update_fields=["auth_subject", "full_name", "updated_at"])
    return user


def record_login(user: User) -> None:
    user.last_login_at = timezone.now()
    user.save(update_fields=["last_login_at", "updated_at"])


@transaction.atomic
def add_guest(*, tenant_id: UUID, name: str, email: str | None, phone: str | None) -> Membership:
    """A person booking without an account: a user with no password and an ACTIVE
    membership with the guest role. Needs app.tenant_id set to tenant_id."""
    free_email = email if email and not find_user_by_email(email) else None
    user = create_user(email=free_email, full_name=name, phone=phone)
    membership = Membership.objects.create(
        tenant_id=tenant_id,
        user=user,
        status=MembershipStatus.ACTIVE,
        display_name=name,
        joined_at=timezone.now(),
    )
    MembershipRole.objects.create(
        tenant_id=tenant_id, membership=membership, role=Role.objects.get(code="guest")
    )
    return membership


def memberships_of_user(user_id: UUID) -> list[dict[str, Any]]:
    """Every tenant the user belongs to, across tenants. Only works with no tenant active:
    RLS policy own_memberships (migration 0003) allows exactly this."""
    rows = (
        Membership.objects.filter(user_id=user_id).select_related("tenant").order_by("created_at")
    )
    return [
        {
            "tenantId": str(m.tenant_id),
            "slug": m.tenant.slug,
            "name": m.tenant.name,
            "memberId": str(m.id),
            "status": m.status.lower(),
        }
        for m in rows
    ]


# ---------- roles ----------


@transaction.atomic
def bootstrap_roles(*, tenant_id: UUID) -> dict[str, Role]:
    """Create the system roles of a new tenant. Needs app.tenant_id set to tenant_id."""
    roles: dict[str, Role] = {}
    for code, (name, permissions) in SYSTEM_ROLES.items():
        role, _ = Role.objects.get_or_create(
            tenant_id=tenant_id, code=code, defaults={"name": name, "is_system": True}
        )
        RolePermission.objects.bulk_create(
            [RolePermission(role=role, permission=p) for p in sorted(permissions)],
            ignore_conflicts=True,
        )
        roles[code] = role
    return roles


def role_permissions(role: Role) -> list[str]:
    """System roles follow the code (constants.SYSTEM_ROLES); others their stored rows."""
    if role.is_system and role.code in SYSTEM_ROLES:
        return sorted(SYSTEM_ROLES[role.code][1])
    return sorted(RolePermission.objects.filter(role=role).values_list("permission", flat=True))


def list_roles() -> list[Role]:
    return list(Role.objects.order_by("-is_system", "code"))


def get_role(role_id: UUID) -> Role:
    try:
        return Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        raise NotFound("No role with this id.") from None


def _check_permissions(codes: list[str]) -> list[str]:
    unknown = sorted(set(codes) - ALL_PERMISSIONS)
    if unknown:
        raise ValidationFailed.one(
            "permissions", f"Unknown permission codes: {', '.join(unknown)}."
        )
    return sorted(set(codes))


@transaction.atomic
def create_role(*, tenant_id: UUID, code: str, name: str, permissions: list[str]) -> Role:
    if not ROLE_CODE.match(code):
        raise ValidationFailed.one("code", "Use snake_case: a-z, 0-9 and _, 2-41 characters.")
    if code in SYSTEM_ROLES or Role.objects.filter(code=code).exists():
        raise ValidationFailed.one("code", "A role with this code already exists.")
    codes = _check_permissions(permissions)
    role = Role.objects.create(tenant_id=tenant_id, code=code, name=name, is_system=False)
    RolePermission.objects.bulk_create([RolePermission(role=role, permission=p) for p in codes])
    return role


@transaction.atomic
def set_role_permissions(*, role_id: UUID, permissions: list[str], name: str | None) -> Role:
    """Replace a custom role's permissions: on = a row, off = no row."""
    role = get_role(role_id)
    if role.is_system:
        raise InvalidTransition("System roles follow the product; create your own role instead.")
    codes = _check_permissions(permissions)
    RolePermission.objects.filter(role=role).exclude(permission__in=codes).delete()
    RolePermission.objects.bulk_create(
        [RolePermission(role=role, permission=p) for p in codes], ignore_conflicts=True
    )
    if name:
        role.name = name
        role.save(update_fields=["name"])
    return role


# ---------- members ----------


@dataclass(frozen=True, slots=True)
class RoleGrant:
    role_id: UUID
    location_id: UUID | None


def _roles_by_code() -> dict[str, Role]:
    return {r.code: r for r in Role.objects.all()}


def resolve_grants(grants: list[dict[str, Any]]) -> list[RoleGrant]:
    """[{role: code | roleId, siteId?}] -> checked RoleGrants."""
    if not grants:
        raise ValidationFailed.one("roles", "Give at least one role.")
    by_code = _roles_by_code()
    by_id = {r.id: r for r in by_code.values()}
    out: list[RoleGrant] = []
    for i, grant in enumerate(grants):
        ref = str(grant.get("role", ""))
        role = by_code.get(ref)
        if role is None:
            try:
                role = by_id.get(UUID(ref))
            except ValueError:
                role = None
        if role is None:
            raise ValidationFailed.one(f"roles[{i}].role", "No role with this code or id.")
        site = grant.get("siteId")
        if site is not None:
            try:
                resources.get_location(site)
            except NotFound:
                raise ValidationFailed.one(f"roles[{i}].siteId", "No site with this id.") from None
        out.append(RoleGrant(role_id=role.id, location_id=site))
    return out


def _grant(tenant_id: UUID, membership: Membership, grants: list[RoleGrant]) -> None:
    for g in grants:
        MembershipRole.objects.get_or_create(
            tenant_id=tenant_id, membership=membership, role_id=g.role_id, location_id=g.location_id
        )


@transaction.atomic
def add_member(
    *,
    tenant_id: UUID,
    user_id: UUID,
    role_code: str,
    location_id: UUID | None = None,
    display_name: str | None = None,
) -> Membership:
    """Used by the platform commands (create_tenant, add_member): active at once."""
    membership, _ = Membership.objects.get_or_create(
        tenant_id=tenant_id,
        user_id=user_id,
        defaults={
            "status": MembershipStatus.ACTIVE,
            "display_name": display_name,
            "joined_at": timezone.now(),
        },
    )
    role = Role.objects.get(tenant_id=tenant_id, code=role_code)
    MembershipRole.objects.get_or_create(
        tenant_id=tenant_id, membership=membership, role=role, location_id=location_id
    )
    return membership


@transaction.atomic
def invite_member(
    *,
    access: Access,
    email: str,
    display_name: str | None,
    grants: list[RoleGrant],
) -> Membership:
    """API_KICH_BAN.md 5.1: user (if new) -> membership INVITED -> roles -> member.invited.

    The invited person signs in with a token carrying this email (verified) and calls
    POST /me/accept-invitation."""
    email = email.strip().lower()
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User.objects.create(auth_subject=INVITE_PREFIX + email, email=email)
    if Membership.objects.filter(user=user).exists():
        raise ValidationFailed.one("email", "This person is already a member or invited.")
    membership = Membership.objects.create(
        tenant_id=access.tenant_id,
        user=user,
        status=MembershipStatus.INVITED,
        display_name=display_name,
        invited_by_id=access.membership_id,
    )
    _grant(access.tenant_id, membership, grants)
    record_status(
        tenant_id=access.tenant_id,
        object_code="membership",
        record_id=membership.id,
        action="invite",
        from_status=None,
        to_status=MembershipStatus.INVITED,
        membership_id=access.membership_id,
    )
    events.emit_event(
        tenant_id=access.tenant_id,
        name="member.invited",
        subject_type="membership",
        subject_id=membership.id,
        actor=events.user_actor(access.membership_id),
        data={"email": email},
    )
    return membership


def invited_membership(*, user_id: UUID, tenant_id: UUID) -> Membership | None:
    return Membership.objects.filter(
        tenant_id=tenant_id, user_id=user_id, status=MembershipStatus.INVITED
    ).first()


@transaction.atomic
def accept_invitation(*, user_id: UUID, tenant_id: UUID) -> Membership:
    membership = (
        Membership.objects.select_for_update().filter(tenant_id=tenant_id, user_id=user_id).first()
    )
    if membership is None:
        raise Forbidden("You have no invitation to this tenant.")
    if membership.status != MembershipStatus.INVITED:
        raise InvalidTransition(f"This membership is {membership.status.lower()}, not invited.")
    return _move(membership, "accept", MembershipStatus.ACTIVE, actor=membership.id)


def _move(membership: Membership, action: str, to: str, *, actor: UUID) -> Membership:
    before = membership.status
    membership.status = to
    fields = ["status", "updated_at"]
    if action == "accept":
        membership.joined_at = timezone.now()
        fields.append("joined_at")
    membership.save(update_fields=fields)
    record_status(
        tenant_id=membership.tenant_id,
        object_code="membership",
        record_id=membership.id,
        action=action,
        from_status=before,
        to_status=to,
        membership_id=actor,
    )
    names = {"accept": "member.joined", "disable": "member.disabled", "enable": "member.enabled"}
    events.emit_event(
        tenant_id=membership.tenant_id,
        name=names[action],
        subject_type="membership",
        subject_id=membership.id,
        actor=events.user_actor(actor),
        changes={"status": {"from": before, "to": to}},
    )
    return membership


def get_member(membership_id: UUID) -> Membership:
    try:
        return Membership.objects.select_related("user").get(id=membership_id)
    except Membership.DoesNotExist:
        raise NotFound("No member with this id.") from None


@transaction.atomic
def set_member_status(*, access: Access, membership_id: UUID, disable: bool) -> Membership:
    membership = get_member(membership_id)
    if membership.id == access.membership_id:
        raise InvalidTransition("You cannot disable or enable yourself.")
    if disable:
        if membership.status == MembershipStatus.DISABLED:
            raise InvalidTransition("This member is already disabled.")
        return _move(membership, "disable", MembershipStatus.DISABLED, actor=access.membership_id)
    if membership.status != MembershipStatus.DISABLED:
        raise InvalidTransition("Only a disabled member can be enabled.")
    return _move(membership, "enable", MembershipStatus.ACTIVE, actor=access.membership_id)


@transaction.atomic
def set_member_roles(*, access: Access, membership_id: UUID, grants: list[RoleGrant]) -> Membership:
    """Replace every role assignment of a member."""
    membership = get_member(membership_id)
    if membership.id == access.membership_id:
        raise InvalidTransition("Ask another admin to change your own roles.")
    MembershipRole.objects.filter(membership=membership).delete()
    _grant(access.tenant_id, membership, grants)
    events.emit_event(
        tenant_id=access.tenant_id,
        name="member.roles_changed",
        subject_type="membership",
        subject_id=membership.id,
        actor=events.user_actor(access.membership_id),
        data={"roles": [{"roleId": str(g.role_id), "siteId": _str(g.location_id)} for g in grants]},
    )
    return membership


def _str(value: UUID | None) -> str | None:
    return str(value) if value else None


def list_members_qs(
    *, status: str | None = None, search: str | None = None
) -> QuerySet[Membership]:
    qs = Membership.objects.select_related("user")
    if status:
        qs = qs.filter(status=status.upper())
    if search:
        qs = qs.filter(
            Q(display_name__icontains=search)
            | Q(user__email__icontains=search)
            | Q(user__full_name__icontains=search)
        )
    return qs


def grants_of(membership_ids: list[UUID]) -> dict[UUID, list[dict[str, Any]]]:
    out: dict[UUID, list[dict[str, Any]]] = {m: [] for m in membership_ids}
    for mr in MembershipRole.objects.filter(membership_id__in=membership_ids).select_related(
        "role"
    ):
        out[mr.membership_id].append(
            {"roleId": str(mr.role_id), "role": mr.role.code, "siteId": _str(mr.location_id)}
        )
    return out


# ---------- access ----------


def resolve_access(*, user_id: UUID, tenant_id: UUID) -> Access | None:
    """The caller's ACTIVE membership in the tenant with its permissions, or None.

    Runs after app.tenant_id is set, so RLS already limits every row to this tenant.
    """
    membership = (
        Membership.objects.filter(
            tenant_id=tenant_id, user_id=user_id, status=MembershipStatus.ACTIVE
        )
        .only("id")
        .first()
    )
    if membership is None:
        return None
    assignments = MembershipRole.objects.filter(membership=membership).values_list(
        "role_id", "role__code", "role__is_system", "location_id"
    )
    role_scopes: dict[UUID, set[UUID | None]] = defaultdict(set)
    role_codes: set[str] = set()
    permissions: dict[str, set[UUID | None]] = defaultdict(set)
    custom: list[UUID] = []
    for role_id, code, is_system, location_id in assignments:
        role_scopes[role_id].add(location_id)
        role_codes.add(code)
        if is_system and code in SYSTEM_ROLES:
            for permission in SYSTEM_ROLES[code][1]:
                permissions[permission].add(location_id)
        else:
            custom.append(role_id)
    for role_id, permission in RolePermission.objects.filter(role_id__in=custom).values_list(
        "role_id", "permission"
    ):
        permissions[permission] |= role_scopes[role_id]
    return Access(
        tenant_id=tenant_id,
        user_id=user_id,
        membership_id=membership.id,
        roles=frozenset(role_codes),
        permissions={k: frozenset(v) for k, v in permissions.items()},
    )


def membership_exists(*, tenant_id: UUID, membership_id: UUID) -> bool:
    return Membership.objects.filter(
        tenant_id=tenant_id, id=membership_id, status=MembershipStatus.ACTIVE
    ).exists()


def role_codes_of(*, membership_id: UUID) -> list[str]:
    """Role codes of a member, used as `user.roles` in the rule context."""
    return sorted(
        set(
            MembershipRole.objects.filter(membership_id=membership_id).values_list(
                "role__code", flat=True
            )
        )
    )


def member_label(membership_id: UUID) -> str:
    m = Membership.objects.select_related("user").filter(id=membership_id).first()
    if m is None:
        return ""
    return m.display_name or m.user.full_name or m.user.email or ""
