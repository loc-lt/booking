"""Booking rules: read the current rule set, publish a new one, see past versions."""

from typing import Any
from uuid import UUID

from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from kernel import permissions as perms
from kernel.access import TenantAPIView, require_perm
from kernel.errors import NotFound
from modules.resources import service as resources
from modules.rules import service
from modules.rules.models import RuleSetVersion


class PublishRulesRequest(serializers.Serializer):
    baseVersion = serializers.IntegerField(min_value=0)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    rules = serializers.ListField(child=serializers.DictField(), allow_empty=True, max_length=200)


def rule_set_json(row: RuleSetVersion | None, with_rules: bool = True) -> dict[str, Any]:
    if row is None:
        return {"version": 0, "rules": [], "note": None, "publishedBy": None, "publishedAt": None}
    out: dict[str, Any] = {
        "version": row.version,
        "note": row.note,
        "publishedBy": str(row.published_by_membership_id)
        if row.published_by_membership_id
        else None,
        "publishedAt": row.published_at.isoformat(),
        "ruleCount": len(row.rules),
    }
    if with_rules:
        out["rules"] = row.rules
    return out


def _exists(check: Any) -> Any:
    def run(value: str) -> bool:
        try:
            check(value)
        except (NotFound, ValueError):
            return False
        return True

    return run


def _type_key_exists(key: str) -> bool:
    return resources.list_resource_types_qs().filter(code=key).exists()


class RuleSetView(TenantAPIView):
    def get(self, request: Request) -> Response:
        require_perm(request.access, perms.RULE_READ)
        _, _, row = service.current_rule_set()
        return Response(rule_set_json(row))

    def put(self, request: Request) -> Response:
        require_perm(request.access, perms.RULE_PUBLISH)
        body = PublishRulesRequest(data=request.data)
        body.is_valid(raise_exception=True)
        d = body.validated_data
        row = service.publish(
            tenant_id=request.access.tenant_id,
            base_version=d["baseVersion"],
            rules=d["rules"],
            note=d.get("note") or None,
            membership_id=request.access.membership_id,
            site_exists=_exists(lambda v: resources.get_location(UUID(v))),
            type_key_exists=_type_key_exists,
            resource_exists=_exists(lambda v: resources.get_resource(UUID(v))),
        )
        return Response(rule_set_json(row))


class RuleVersionListView(TenantAPIView):
    def get(self, request: Request) -> Response:
        require_perm(request.access, perms.RULE_READ)
        return Response({"data": [rule_set_json(r, False) for r in service.list_versions()]})


class RuleVersionDetailView(TenantAPIView):
    def get(self, request: Request, version: int) -> Response:
        require_perm(request.access, perms.RULE_READ)
        row = service.get_version(version)
        if row is None:
            raise NotFound("No rule set with this version.")
        return Response(rule_set_json(row))
