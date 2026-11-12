"""Rewrite stored rule sets to the second rule shape (docs/domain/rules.md, drift report pass 2).

Old: {name, scope.resourceType (key), stage, effect{type,...}, when over user.groups}
New: {label, scope.resourceTypeId (uuid), consequence, limit?, when over user.roles}

Every version is rewritten in place, so old bookings' ruleSetVersion still names readable
rules. The app role has no BYPASSRLS, so each tenant's rows are read inside its own
app.tenant_id. Rules already in the new shape are left as they are.
"""

import json
from typing import Any

from django.db import migrations

EFFECT_TO_LIMIT = {
    "max_duration": ("max_duration", ("minutes",)),
    "advance_window": ("max_advance", ("days",)),
    "quota": ("quota", ("per", "maxBookings", "maxMinutes")),
}


def _roles(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _roles(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_roles(v) for v in node]
    if node == "user.groups":
        return "user.roles"
    return node


def upgrade(rule: dict[str, Any], type_ids: dict[str, str]) -> dict[str, Any]:
    if "consequence" in rule:
        return rule
    new: dict[str, Any] = {"id": rule["id"]}
    if rule.get("name"):
        new["label"] = rule["name"]
    scope = dict(rule.get("scope") or {})
    if "resourceType" in scope:
        key = scope.pop("resourceType")
        # A key with no type left can match nothing; keep it visible instead of dropping it.
        scope["resourceTypeId"] = type_ids.get(key, "00000000-0000-0000-0000-000000000000")
    if scope:
        new["scope"] = scope
    if "priority" in rule:
        new["priority"] = rule["priority"]
    when = _roles(rule.get("when"))
    effect = rule.get("effect") or {}
    kind = effect.get("type")
    if kind == "require_approval":
        new["consequence"] = "require_approval"
    elif kind == "allowed_groups":
        allowed = {"or": [{"in": [g, {"var": "user.roles"}]} for g in effect.get("groups", [])]}
        outsider = {"!": [allowed]}
        when = outsider if when is None else {"and": [when, outsider]}
        new["consequence"] = "deny"
    elif kind in EFFECT_TO_LIMIT:
        limit_type, keys = EFFECT_TO_LIMIT[kind]
        new["consequence"] = "deny"
        new["limit"] = {"type": limit_type, **{k: effect[k] for k in keys if k in effect}}
    else:
        new["consequence"] = "deny"
    if when is not None:
        new["when"] = when
    if rule.get("message"):
        new["message"] = rule["message"]
    new["enabled"] = rule.get("enabled", True)
    return new


def forward(apps: Any, schema_editor: Any) -> None:
    with schema_editor.connection.cursor() as cur:
        cur.execute("SELECT id FROM tenants")
        tenant_ids = [str(r[0]) for r in cur.fetchall()]
        for tenant_id in tenant_ids:
            cur.execute("SELECT set_config('app.tenant_id', %s, true)", [tenant_id])
            cur.execute("SELECT code, id FROM resource_types")
            type_ids = {code: str(rt_id) for code, rt_id in cur.fetchall()}
            cur.execute("SELECT id, rules FROM rule_set_versions")
            for row_id, rules in cur.fetchall():
                if isinstance(rules, str):
                    rules = json.loads(rules)
                upgraded = [upgrade(r, type_ids) for r in rules]
                if upgraded != rules:
                    cur.execute(
                        "UPDATE rule_set_versions SET rules = %s::jsonb WHERE id = %s",
                        [json.dumps(upgraded), row_id],
                    )
        cur.execute("SELECT set_config('app.tenant_id', '', true)")


class Migration(migrations.Migration):
    dependencies = [
        ("rules", "0002_db_rules"),
        ("resources", "0001_initial"),
        ("tenancy", "0001_initial"),
    ]

    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
