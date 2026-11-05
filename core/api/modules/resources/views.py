"""Thin views: permission -> request serializer -> one service call -> response."""

from typing import Any
from uuid import UUID

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from kernel import permissions as perms
from kernel.access import TenantAPIView, require_perm, require_somewhere
from kernel.errors import ValidationFailed
from kernel.pagination import paginate
from kernel.params import uuid_param
from modules.booking import service as booking
from modules.config import service as config
from modules.resources import serializers as s
from modules.resources import service
from modules.resources.models import ResourceStatus


def _types_json(rows: list[Any]) -> list[dict[str, Any]]:
    return [s.resource_type_json(v) for v in service.describe_types(rows)]


def _type(row: Any) -> dict[str, Any]:
    return _types_json([row])[0]


# ---------- sites ----------


class SiteListView(TenantAPIView):
    def get(self, request: Request) -> Response:
        require_somewhere(request.access, perms.SITE_READ)
        page = paginate(
            service.list_locations_qs(),
            request.query_params,
            lambda rows: [s.site_json(r) for r in rows],
        )
        return Response(page)

    def post(self, request: Request) -> Response:
        require_perm(request.access, perms.SITE_MANAGE)
        body = s.CreateSiteRequest(data=request.data)
        body.is_valid(raise_exception=True)
        d = body.validated_data
        row = service.create_location(
            tenant_id=request.access.tenant_id,
            code=d.get("code"),
            name=d["name"],
            timezone_name=d["timezone"],
            address=d["address"],
        )
        return Response(s.site_json(row), status=status.HTTP_201_CREATED)


class SiteDetailView(TenantAPIView):
    def get(self, request: Request, site_id: UUID) -> Response:
        require_perm(request.access, perms.SITE_READ, site_id)
        return Response(s.site_json(service.get_location(site_id)))

    def patch(self, request: Request, site_id: UUID) -> Response:
        require_perm(request.access, perms.SITE_MANAGE, site_id)
        body = s.UpdateSiteRequest(data=request.data)
        body.is_valid(raise_exception=True)
        d = body.validated_data
        row = service.update_location(
            location_id=site_id, name=d.get("name"), address=d.get("address")
        )
        return Response(s.site_json(row))


# ---------- resource types ----------


class ResourceTypeListView(TenantAPIView):
    def get(self, request: Request) -> Response:
        require_perm(request.access, perms.RESOURCE_TYPE_READ)
        page = paginate(service.list_resource_types_qs(), request.query_params, _types_json)
        return Response(page)

    def post(self, request: Request) -> Response:
        require_perm(request.access, perms.RESOURCE_TYPE_MANAGE)
        body = s.CreateResourceTypeRequest(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        row = service.create_resource_type(
            tenant_id=request.access.tenant_id,
            key=data["key"],
            label=data["label"],
            fields=data["fields"],
            flow_config=data["flowConfig"],
            membership_id=request.access.membership_id,
            slot_minutes=data["slotMinutes"],
        )
        return Response(_type(row), status=status.HTTP_201_CREATED)


class ResourceTypeDetailView(TenantAPIView):
    def get(self, request: Request, resource_type_id: UUID) -> Response:
        require_perm(request.access, perms.RESOURCE_TYPE_READ)
        return Response(_type(service.get_resource_type(resource_type_id)))

    def patch(self, request: Request, resource_type_id: UUID) -> Response:
        require_perm(request.access, perms.RESOURCE_TYPE_MANAGE)
        body = s.UpdateResourceTypeRequest(data=request.data)
        body.is_valid(raise_exception=True)
        d = body.validated_data
        row = service.update_flow_config(
            resource_type_id=resource_type_id,
            base_version=d["baseVersion"],
            flow_config=d["flowConfig"],
            membership_id=request.access.membership_id,
            label=d.get("label"),
            slot_minutes=d.get("slotMinutes"),
        )
        return Response(_type(row))


class ResourceTypeFieldsView(TenantAPIView):
    """POST /resource-types/{id}/fields: add fields, publish the new form."""

    def post(self, request: Request, resource_type_id: UUID) -> Response:
        require_perm(request.access, perms.RESOURCE_TYPE_MANAGE)
        body = s.AddFieldsRequest(data=request.data)
        body.is_valid(raise_exception=True)
        row = service.add_fields(
            resource_type_id=resource_type_id,
            fields=body.validated_data["fields"],
            membership_id=request.access.membership_id,
        )
        return Response(_type(row))


class ResourceTypeFieldArchiveView(TenantAPIView):
    def post(self, request: Request, resource_type_id: UUID, key: str) -> Response:
        require_perm(request.access, perms.RESOURCE_TYPE_MANAGE)
        row = service.archive_field(
            resource_type_id=resource_type_id, key=key, membership_id=request.access.membership_id
        )
        return Response(_type(row))


class ResourceTypeVersionsView(TenantAPIView):
    def get(self, request: Request, resource_type_id: UUID) -> Response:
        require_perm(request.access, perms.RESOURCE_TYPE_READ)
        service.get_resource_type(resource_type_id)
        return Response(
            {
                "data": [
                    {
                        "version": v.version,
                        "status": v.status.lower(),
                        "basedOnVersion": v.based_on_version,
                        "flowConfig": v.flow_config,
                        "publishedBy": (
                            str(v.published_by_membership_id)
                            if v.published_by_membership_id
                            else None
                        ),
                        "publishedAt": v.published_at.isoformat() if v.published_at else None,
                    }
                    for v in config.list_policy_versions(resource_type_id)
                ]
            }
        )


class ResourceTypeRestoreView(TenantAPIView):
    def post(self, request: Request, resource_type_id: UUID, version: int) -> Response:
        require_perm(request.access, perms.POLICY_PUBLISH)
        body = s.RestoreVersionRequest(data=request.data)
        body.is_valid(raise_exception=True)
        row = service.restore_policy_version(
            resource_type_id=resource_type_id,
            version=version,
            base_version=body.validated_data["baseVersion"],
            membership_id=request.access.membership_id,
        )
        return Response(_type(row))


# ---------- resources ----------


class ResourceListView(TenantAPIView):
    def get(self, request: Request) -> Response:
        require_perm(request.access, perms.RESOURCE_READ)
        wanted = request.query_params.get("status")
        if wanted and wanted.upper() not in ResourceStatus.values:
            raise ValidationFailed.one("status", "Use active, maintenance, inactive.")
        qs = service.list_resources_qs(
            resource_type_id=uuid_param(request.query_params, "resourceTypeId"),
            location_id=uuid_param(request.query_params, "siteId"),
            status=wanted,
        )
        page = paginate(qs, request.query_params, lambda rows: [s.resource_json(r) for r in rows])
        return Response(page)

    def post(self, request: Request) -> Response:
        body = s.CreateResourceRequest(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        require_perm(request.access, perms.RESOURCE_MANAGE, location_id=data["siteId"])
        row = service.create_resource(
            tenant_id=request.access.tenant_id,
            resource_type_id=data["resourceTypeId"],
            location_id=data["siteId"],
            label=data["label"],
            custom_field_values=data["customFieldValues"],
            membership_id=request.access.membership_id,
            capacity=data["capacity"],
        )
        return Response(s.resource_json(row), status=status.HTTP_201_CREATED)


class ResourceDetailView(TenantAPIView):
    def get(self, request: Request, resource_id: UUID) -> Response:
        require_perm(request.access, perms.RESOURCE_READ)
        return Response(s.resource_json(service.get_resource(resource_id)))

    def patch(self, request: Request, resource_id: UUID) -> Response:
        current = service.get_resource(resource_id)
        require_perm(request.access, perms.RESOURCE_MANAGE, current.location_id)
        body = s.UpdateResourceRequest(data=request.data)
        body.is_valid(raise_exception=True)
        d = body.validated_data
        row = service.update_resource(
            resource_id=resource_id,
            label=d.get("label"),
            custom_field_values=d.get("customFieldValues"),
            membership_id=request.access.membership_id,
        )
        return Response(s.resource_json(row))


class ResourceMoveView(TenantAPIView):
    """POST /resources/{id}/maintenance | /activate | /deactivate. Returns the resource and
    the open bookings still on it, for an admin to decide about (nothing is auto-cancelled)."""

    move = ""

    def post(self, request: Request, resource_id: UUID) -> Response:
        current = service.get_resource(resource_id)
        require_perm(request.access, perms.RESOURCE_MANAGE, current.location_id)
        body = s.ResourceMoveRequest(data=request.data)
        body.is_valid(raise_exception=True)
        row = service.move_resource(
            resource_id=resource_id,
            move=self.move,
            membership_id=request.access.membership_id,
            reason=body.validated_data.get("reason") or None,
        )
        affected = (
            booking.upcoming_on(resource_ids=[row.id])
            if row.status != ResourceStatus.ACTIVE
            else []
        )
        return Response({"resource": s.resource_json(row), "affectedBookings": affected})


class ResourceMaintenanceView(ResourceMoveView):
    move = "maintenance"


class ResourceActivateView(ResourceMoveView):
    move = "activate"


class ResourceDeactivateView(ResourceMoveView):
    move = "deactivate"
