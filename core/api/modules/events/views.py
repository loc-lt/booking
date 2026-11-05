"""GET /events: the tenant's event log (outbox), newest first, with delivery state.

The outbox has no RLS (the worker reads across tenants), so this view always filters by the
caller's tenant explicitly."""

from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from kernel import permissions as perms
from kernel.access import TenantAPIView, require_perm
from kernel.pagination import paginate
from kernel.params import uuid_param
from modules.events.models import Outbox


def events_json(rows: list[Outbox]) -> list[dict[str, Any]]:
    return [
        {
            **row.payload,
            "delivery": {
                "publishedAt": row.published_at.isoformat() if row.published_at else None,
                "attempts": row.attempts,
                "lastError": row.last_error,
            },
        }
        for row in rows
    ]


class EventListView(TenantAPIView):
    def get(self, request: Request) -> Response:
        require_perm(request.access, perms.AUDIT_READ)
        qs = Outbox.objects.filter(tenant_id=request.access.tenant_id)
        subject = uuid_param(request.query_params, "subjectId")
        if subject:
            qs = qs.filter(aggregate_id=subject)
        name = request.query_params.get("name")
        if name:
            qs = qs.filter(event_type__startswith=name)
        return Response(paginate(qs, request.query_params, events_json))
