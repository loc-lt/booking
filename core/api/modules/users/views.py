"""People: who am I, roles, members, invitations (API_KICH_BAN.md section 5)."""

from typing import Any
from uuid import UUID

from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from kernel import permissions as perms
from kernel.access import TenantAPIView, parse_tenant_header, require_perm, require_somewhere
from kernel.errors import ValidationFailed
from kernel.pagination import paginate
from kernel.tenant_context import activate_tenant
from modules.users import service
from modules.users.models import Membership, MembershipStatus, Role

# ---------- shapes ----------


class GrantSerializer(serializers.Serializer):
    role = serializers.CharField(max_length=64, help_text="Role code (e.g. staff) or role id")
    siteId = serializers.UUIDField(required=False, allow_null=True, default=None)


class InviteRequest(serializers.Serializer):
    email = serializers.EmailField()
    displayName = serializers.CharField(max_length=200, required=False, allow_blank=True)
    roles = GrantSerializer(many=True)


class SetRolesRequest(serializers.Serializer):
    roles = GrantSerializer(many=True)


class CreateRoleRequest(serializers.Serializer):
    code = serializers.CharField(max_length=41)
    name = serializers.CharField(max_length=200)
    permissions = serializers.ListField(child=serializers.CharField(), allow_empty=True)


class SetPermissionsRequest(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    permissions = serializers.ListField(child=serializers.CharField(), allow_empty=True)


def role_json(role: Role) -> dict[str, Any]:
    return {
        "id": str(role.id),
        "code": role.code,
        "name": role.name,
        "isSystem": role.is_system,
        "permissions": service.role_permissions(role),
        "createdAt": role.created_at.isoformat(),
    }


def members_json(rows: list[Membership]) -> list[dict[str, Any]]:
    grants = service.grants_of([m.id for m in rows])
    return [
        {
            "id": str(m.id),
            "userId": str(m.user_id),
            "email": m.user.email,
            "displayName": m.display_name or m.user.full_name or None,
            "status": m.status.lower(),
            "roles": grants[m.id],
            "invitedBy": str(m.invited_by_id) if m.invited_by_id else None,
            "joinedAt": m.joined_at.isoformat() if m.joined_at else None,
            "createdAt": m.created_at.isoformat(),
        }
        for m in rows
    ]


def _member(membership_id: UUID) -> dict[str, Any]:
    return members_json([service.get_member(membership_id)])[0]


# ---------- me ----------


class MeView(TenantAPIView):
    def get(self, request: Request) -> Response:
        a = request.access
        return Response(
            {
                "userId": str(a.user_id),
                "tenantId": str(a.tenant_id),
                "member": _member(a.membership_id),
                "permissions": {
                    code: sorted("*" if s is None else str(s) for s in scopes)
                    for code, scopes in sorted(a.permissions.items())
                },
            }
        )


class AcceptInvitationView(APIView):
    """The only call a not-yet-active member may make: no Access is resolved."""

    def post(self, request: Request) -> Response:
        tenant_id = parse_tenant_header(request.headers.get("X-Tenant-Id"))
        activate_tenant(tenant_id)
        membership = service.accept_invitation(user_id=request.user.user_id, tenant_id=tenant_id)
        return Response(_member(membership.id))


# ---------- permissions and roles ----------


class PermissionListView(TenantAPIView):
    def get(self, request: Request) -> Response:
        return Response(
            {
                "data": [
                    {"code": code, "description": text}
                    for code, text in sorted(perms.DESCRIPTIONS.items())
                ]
            }
        )


class RoleListView(TenantAPIView):
    def get(self, request: Request) -> Response:
        require_somewhere(request.access, perms.MEMBER_READ)
        return Response({"data": [role_json(r) for r in service.list_roles()]})

    def post(self, request: Request) -> Response:
        require_perm(request.access, perms.ROLE_MANAGE)
        body = CreateRoleRequest(data=request.data)
        body.is_valid(raise_exception=True)
        d = body.validated_data
        role = service.create_role(
            tenant_id=request.access.tenant_id,
            code=d["code"],
            name=d["name"],
            permissions=d["permissions"],
        )
        return Response(role_json(role), status=status.HTTP_201_CREATED)


class RolePermissionsView(TenantAPIView):
    def put(self, request: Request, role_id: UUID) -> Response:
        require_perm(request.access, perms.ROLE_MANAGE)
        body = SetPermissionsRequest(data=request.data)
        body.is_valid(raise_exception=True)
        role = service.set_role_permissions(
            role_id=role_id,
            permissions=body.validated_data["permissions"],
            name=body.validated_data.get("name"),
        )
        return Response(role_json(role))


# ---------- members ----------


class MemberListView(TenantAPIView):
    def get(self, request: Request) -> Response:
        require_somewhere(request.access, perms.MEMBER_READ)
        wanted = request.query_params.get("status")
        if wanted and wanted.upper() not in MembershipStatus.values:
            raise ValidationFailed.one("status", "Use invited, active or disabled.")
        qs = service.list_members_qs(status=wanted, search=request.query_params.get("q"))
        return Response(paginate(qs, request.query_params, members_json))


class MemberInviteView(TenantAPIView):
    def post(self, request: Request) -> Response:
        require_perm(request.access, perms.MEMBER_MANAGE)
        body = InviteRequest(data=request.data)
        body.is_valid(raise_exception=True)
        d = body.validated_data
        membership = service.invite_member(
            access=request.access,
            email=d["email"],
            display_name=d.get("displayName") or None,
            grants=service.resolve_grants(d["roles"]),
        )
        return Response(_member(membership.id), status=status.HTTP_201_CREATED)


class MemberDetailView(TenantAPIView):
    def get(self, request: Request, membership_id: UUID) -> Response:
        if membership_id != request.access.membership_id:
            require_somewhere(request.access, perms.MEMBER_READ)
        return Response(_member(membership_id))


class MemberRolesView(TenantAPIView):
    def put(self, request: Request, membership_id: UUID) -> Response:
        require_perm(request.access, perms.MEMBER_MANAGE)
        body = SetRolesRequest(data=request.data)
        body.is_valid(raise_exception=True)
        service.set_member_roles(
            access=request.access,
            membership_id=membership_id,
            grants=service.resolve_grants(body.validated_data["roles"]),
        )
        return Response(_member(membership_id))


class MemberDisableView(TenantAPIView):
    disable = True

    def post(self, request: Request, membership_id: UUID) -> Response:
        require_perm(request.access, perms.MEMBER_MANAGE)
        service.set_member_status(
            access=request.access, membership_id=membership_id, disable=self.disable
        )
        return Response(_member(membership_id))


class MemberEnableView(MemberDisableView):
    disable = False
