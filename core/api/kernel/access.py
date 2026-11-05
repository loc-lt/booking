"""Tenant and permission checks shared by every view.

Flow per request (docs/backend.md, "Data and tenancy"):
  JWT verified (kernel.auth) -> X-Tenant-Id read -> SET LOCAL app.tenant_id
  -> the caller's ACTIVE membership in that tenant is loaded -> permissions resolved.
No membership -> 403 FORBIDDEN, and the transaction is rolled back.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from django.utils.module_loading import import_string
from rest_framework.request import Request
from rest_framework.views import APIView

from kernel.errors import Forbidden, ValidationFailed
from kernel.tenant_context import activate_tenant

ALL_LOCATIONS = None


@dataclass(frozen=True, slots=True)
class Access:
    """Who is calling, in which tenant, allowed to do what, where.

    permissions maps a permission code to the location ids it applies to. A None entry means
    every location of the tenant.
    """

    tenant_id: UUID
    user_id: UUID
    membership_id: UUID
    roles: frozenset[str]
    permissions: dict[str, frozenset[UUID | None]] = field(default_factory=dict)

    def can(self, permission: str, location_id: UUID | None = None) -> bool:
        scopes = self.permissions.get(permission)
        if not scopes:
            return False
        return ALL_LOCATIONS in scopes or (location_id is not None and location_id in scopes)

    def locations_for(self, permission: str) -> frozenset[UUID | None]:
        return self.permissions.get(permission, frozenset())


def require_perm(access: Access, permission: str, location_id: UUID | None = None) -> None:
    if not access.can(permission, location_id):
        raise Forbidden(f"Missing permission {permission}.")


def require_somewhere(access: Access, permission: str) -> None:
    """For tenant-wide lists (members, roles): holding the permission at any site is enough."""
    if not access.permissions.get(permission):
        raise Forbidden(f"Missing permission {permission}.")


def require_any(
    access: Access, permissions: Iterable[str], location_id: UUID | None = None
) -> None:
    if not any(access.can(p, location_id) for p in permissions):
        raise Forbidden("Missing permission.")


def _access_resolver() -> Any:
    # By path, so the kernel does not import the users module.
    return import_string("modules.users.service.resolve_access")


def parse_tenant_header(raw: str | None) -> UUID:
    if not raw:
        raise ValidationFailed.one("X-Tenant-Id", "This header is required.")
    try:
        return UUID(raw)
    except ValueError:
        raise ValidationFailed.one("X-Tenant-Id", "Must be a UUID.") from None


class TenantAPIView(APIView):
    """Base view for every /api/v1 endpoint. After DRF authenticates the JWT, it activates
    the tenant for the request transaction and puts `request.access` on the request."""

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)  # authentication + IsAuthenticated
        tenant_id = parse_tenant_header(request.headers.get("X-Tenant-Id"))
        activate_tenant(tenant_id)
        access = _access_resolver()(user_id=request.user.user_id, tenant_id=tenant_id)
        if access is None:
            raise Forbidden("You are not a member of this tenant.")
        request.access = access
