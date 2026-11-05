"""Availability: free-slot search, opening hours, exceptions (API_KICH_BAN.md 4.2, 4.3, 6.1)."""

from datetime import time
from typing import Any
from uuid import UUID

from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from kernel import permissions as perms
from kernel.access import TenantAPIView, require_perm, require_somewhere
from kernel.errors import ValidationFailed
from kernel.pagination import paginate
from kernel.params import datetime_param, uuid_param
from kernel.serializers import AwareDateTimeField
from modules.availability import service
from modules.availability.models import AvailabilityException
from modules.availability.search import search
from modules.booking import service as booking
from modules.resources import service as resources


class AvailabilityQuery(serializers.Serializer):
    siteId = serializers.UUIDField()
    resourceTypeId = serializers.UUIDField()
    date = serializers.DateField()
    resourceId = serializers.UUIDField(required=False)


class AvailabilityView(TenantAPIView):
    def get(self, request: Request) -> Response:
        query = AvailabilityQuery(data=request.query_params)
        query.is_valid(raise_exception=True)
        q = query.validated_data
        require_perm(request.access, perms.AVAILABILITY_READ, q["siteId"])
        return Response(
            search(
                site_id=q["siteId"],
                resource_type_id=q["resourceTypeId"],
                day=q["date"],
                resource_id=q.get("resourceId"),
            )
        )


# ---------- opening hours ----------


class HoursRangeSerializer(serializers.Serializer):
    weekday = serializers.IntegerField(min_value=0, max_value=6, help_text="0 = Monday")
    opens = serializers.TimeField(format="%H:%M")
    closes = serializers.TimeField(format="%H:%M")


class SetHoursRequest(serializers.Serializer):
    weekly = HoursRangeSerializer(many=True, allow_empty=True)


def _hours_body(request: Request) -> dict[int, list[tuple[time, time]]]:
    body = SetHoursRequest(data=request.data)
    body.is_valid(raise_exception=True)
    hours: dict[int, list[tuple[time, time]]] = {}
    for r in body.validated_data["weekly"]:
        hours.setdefault(r["weekday"], []).append((r["opens"], r["closes"]))
    return hours


def _weekly_json(rows: list[tuple[int, time, time]]) -> list[dict[str, Any]]:
    return [
        {"weekday": d, "opens": a.strftime("%H:%M"), "closes": b.strftime("%H:%M")}
        for d, a, b in rows
    ]


class SiteHoursView(TenantAPIView):
    def _json(self, site_id: UUID) -> dict[str, Any]:
        site = resources.get_location(site_id)
        return {
            "siteId": str(site.id),
            "timezone": site.timezone,
            "weekly": _weekly_json(service.weekly_hours(location_id=site.id)),
        }

    def get(self, request: Request, site_id: UUID) -> Response:
        require_perm(request.access, perms.SITE_READ, site_id)
        return Response(self._json(site_id))

    def put(self, request: Request, site_id: UUID) -> Response:
        require_perm(request.access, perms.SITE_MANAGE, site_id)
        site = resources.get_location(site_id)
        service.set_weekly_hours(
            tenant_id=request.access.tenant_id, location_id=site.id, hours=_hours_body(request)
        )
        return Response(self._json(site_id))


class ResourceHoursView(TenantAPIView):
    """A resource's own hours replace its site's. DELETE goes back to the site's hours."""

    def _json(self, resource_id: UUID) -> dict[str, Any]:
        resource = resources.get_resource(resource_id)
        own = service.weekly_hours(resource_id=resource.id)
        return {
            "resourceId": str(resource.id),
            "siteId": str(resource.location_id),
            "timezone": resource.location.timezone,
            "inheritsSiteHours": not own,
            "weekly": _weekly_json(own or service.weekly_hours(location_id=resource.location_id)),
        }

    def get(self, request: Request, resource_id: UUID) -> Response:
        require_perm(request.access, perms.RESOURCE_READ)
        return Response(self._json(resource_id))

    def put(self, request: Request, resource_id: UUID) -> Response:
        resource = resources.get_resource(resource_id)
        require_perm(request.access, perms.RESOURCE_MANAGE, resource.location_id)
        service.set_weekly_hours(
            tenant_id=request.access.tenant_id, resource_id=resource.id, hours=_hours_body(request)
        )
        return Response(self._json(resource_id))

    def delete(self, request: Request, resource_id: UUID) -> Response:
        resource = resources.get_resource(resource_id)
        require_perm(request.access, perms.RESOURCE_MANAGE, resource.location_id)
        service.clear_resource_hours(resource_id=resource.id)
        return Response(self._json(resource_id))


# ---------- exceptions ----------


class CreateExceptionRequest(serializers.Serializer):
    siteId = serializers.UUIDField(required=False)
    resourceId = serializers.UUIDField(required=False)
    kind = serializers.ChoiceField(choices=["block", "open"])
    start = AwareDateTimeField()
    end = AwareDateTimeField()
    reasonCode = serializers.ChoiceField(
        choices=["holiday", "maintenance", "private_event", "other"], required=False
    )
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)


def exception_json(e: AvailabilityException) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "siteId": str(e.location_id) if e.location_id else None,
        "resourceId": str(e.resource_id) if e.resource_id else None,
        "kind": e.kind.lower(),
        "start": e.during.lower.isoformat(),
        "end": e.during.upper.isoformat(),
        "reasonCode": e.reason_code,
        "note": e.note,
        "createdBy": str(e.created_by_membership_id) if e.created_by_membership_id else None,
        "createdAt": e.created_at.isoformat(),
    }


def _site_of(site_id: Any, resource_id: UUID | None) -> tuple[UUID, list[UUID]]:
    """(site the exception applies at, resources it covers)."""
    if resource_id:
        resource = resources.get_resource(resource_id)
        return resource.location_id, [resource.id]
    site = resources.get_location(site_id)
    return site.id, resources.resource_ids_at(site.id)


class ExceptionListView(TenantAPIView):
    def get(self, request: Request) -> Response:
        require_somewhere(request.access, perms.SITE_READ)
        qs = service.list_exceptions_qs(
            location_id=uuid_param(request.query_params, "siteId"),
            resource_id=uuid_param(request.query_params, "resourceId"),
            start=datetime_param(request.query_params, "from"),
            end=datetime_param(request.query_params, "to"),
        )
        page = paginate(qs, request.query_params, lambda rows: [exception_json(e) for e in rows])
        return Response(page)

    def post(self, request: Request) -> Response:
        body = CreateExceptionRequest(data=request.data)
        body.is_valid(raise_exception=True)
        d = body.validated_data
        if bool(d.get("siteId")) == bool(d.get("resourceId")):
            raise ValidationFailed.one("siteId", "Give exactly one of siteId, resourceId.")
        site_id, resource_ids = _site_of(d.get("siteId"), d.get("resourceId"))
        require_perm(request.access, perms.AVAILABILITY_MANAGE, site_id)
        row = service.add_exception(
            tenant_id=request.access.tenant_id,
            kind=d["kind"].upper(),
            start=d["start"],
            end=d["end"],
            location_id=d.get("siteId"),
            resource_id=d.get("resourceId"),
            reason_code=d.get("reasonCode"),
            note=d.get("note") or None,
            membership_id=request.access.membership_id,
        )
        affected = (
            booking.upcoming_on(resource_ids=resource_ids, start=d["start"], end=d["end"])
            if d["kind"] == "block"
            else []
        )
        return Response(
            {"exception": exception_json(row), "affectedBookings": affected},
            status=status.HTTP_201_CREATED,
        )


class ExceptionDetailView(TenantAPIView):
    def delete(self, request: Request, exception_id: UUID) -> Response:
        row = service.get_exception(exception_id)
        site_id, _ = _site_of(row.location_id, row.resource_id)
        require_perm(request.access, perms.AVAILABILITY_MANAGE, site_id)
        service.delete_exception(exception_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
