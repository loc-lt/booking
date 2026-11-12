"""Public interface of the rules module: storing, publishing and applying booking rules.

A tenant's rules are one rule set with a version. Publishing replaces the whole set (with
baseVersion, like policies), so a booking can always name the exact rules it was checked
against. The rule shape is docs/examples/rule.json:

  {"id": "guests-max-2h", "label": "...", "scope": {"resourceTypeId": "<uuid>"},
   "priority": 10, "when": <JSONLogic>, "consequence": "deny",
   "limit": {"type": "max_duration", "minutes": 120}, "enabled": true}

scope: {} (whole tenant) | {"siteId"} | {"resourceTypeId"} | {"resourceId"}.
consequence: deny | require_approval | require_payment. `limit` only on deny rules.
"""

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction

from kernel.errors import StaleVersion, ValidationFailed
from modules.events import service as events
from modules.rules import jsonlogic
from modules.rules.engine import CONSEQUENCES, LIMITS, MAX_RULES, Decision, Rule, evaluate_rules
from modules.rules.models import RuleSetVersion

RULE_SET_VERSION_NONE = 0
RULE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
SCOPE_KEYS = ("siteId", "resourceTypeId", "resourceId")

# limit type -> (required keys, optional keys)
LIMIT_KEYS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "max_duration": (("minutes",), ()),
    "max_advance": (("days",), ()),
    "quota": (("per",), ("maxBookings", "maxMinutes")),
}


# ---------- reading ----------


def current_rule_set() -> tuple[int, list[dict[str, Any]], RuleSetVersion | None]:
    row = RuleSetVersion.objects.order_by("-version").first()
    if row is None:
        return RULE_SET_VERSION_NONE, [], None
    return row.version, row.rules, row


def list_versions() -> list[RuleSetVersion]:
    return list(RuleSetVersion.objects.order_by("-version"))


def get_version(version: int) -> RuleSetVersion | None:
    return RuleSetVersion.objects.filter(version=version).first()


def _scope_kind(scope: dict[str, Any]) -> str:
    if "resourceId" in scope:
        return "resource"
    if "resourceTypeId" in scope:
        return "resource_type"
    if "siteId" in scope:
        return "site"
    return "tenant"


def _applies(
    scope: dict[str, Any], location_id: UUID, resource_type_id: UUID, resource_id: UUID
) -> bool:
    kind = _scope_kind(scope)
    if kind == "resource":
        return scope["resourceId"] == str(resource_id)
    if kind == "resource_type":
        return scope["resourceTypeId"] == str(resource_type_id)
    if kind == "site":
        return scope["siteId"] == str(location_id)
    return True


def published_rules(
    *, location_id: UUID, resource_type_id: UUID, resource_id: UUID
) -> tuple[list[Rule], int]:
    """(enabled rules for this booking's scope, most general first; rule set version)."""
    version, raw, _ = current_rule_set()
    picked = [
        r
        for r in raw
        if r.get("enabled", True)
        and _applies(r.get("scope") or {}, location_id, resource_type_id, resource_id)
    ]
    rules = [to_engine(r, version) for r in picked]
    order = {"tenant": 0, "site": 1, "resource_type": 2, "resource": 3}
    return sorted(rules, key=lambda r: order[r.scope]), version


def to_engine(raw: dict[str, Any], version: int = 1) -> Rule:
    return Rule(
        id=raw["id"],
        scope=_scope_kind(raw.get("scope") or {}),
        when=raw.get("when"),
        consequence=raw["consequence"],
        limit=raw.get("limit"),
        priority=int(raw.get("priority", 0)),
        message=raw.get("message") or raw.get("label"),
        version=version,
    )


def decide(rules: list[Rule], context: dict[str, Any]) -> Decision:
    return evaluate_rules(rules, context)


# ---------- publishing ----------


def _check_consequence(i: int, rule: dict[str, Any], errors: list[dict[str, str]]) -> None:
    def err(name: str, message: str) -> None:
        errors.append({"field": f"rules[{i}].{name}", "message": message})

    consequence = rule.get("consequence")
    if consequence not in CONSEQUENCES:
        err("consequence", f"Use one of: {', '.join(CONSEQUENCES)}.")
        return
    if "limit" not in rule:
        return
    limit = rule["limit"]
    if consequence != "deny":
        err("limit", "Only deny rules have a limit.")
        return
    if not isinstance(limit, dict) or limit.get("type") not in LIMITS:
        err("limit.type", f"Use one of: {', '.join(LIMITS)}.")
        return
    required, optional = LIMIT_KEYS[limit["type"]]
    for key in required:
        if key not in limit:
            err(f"limit.{key}", "Required for this limit.")
    unknown = set(limit) - {"type", *required, *optional}
    if unknown:
        err("limit", f"Unknown key {sorted(unknown)[0]}.")
    for key in ("minutes", "days", "maxBookings", "maxMinutes"):
        if key in limit and (not isinstance(limit[key], int) or limit[key] < 0):
            err(f"limit.{key}", "Use a whole number, 0 or more.")
    if limit["type"] == "quota":
        if limit.get("per") not in ("day", "week"):
            err("limit.per", "Use day or week.")
        if "maxBookings" not in limit and "maxMinutes" not in limit:
            err("limit", "A quota needs maxBookings or maxMinutes.")


def _check_scope(
    i: int,
    rule: dict[str, Any],
    errors: list[dict[str, str]],
    exists: dict[str, Callable[[str], bool]],
    priced: Callable[[str, str], bool],
) -> None:
    scope = rule.get("scope") or {}
    if not isinstance(scope, dict) or len(scope) > 1:
        errors.append(
            {
                "field": f"rules[{i}].scope",
                "message": "Empty (whole tenant) or one of siteId, resourceTypeId, resourceId.",
            }
        )
        return
    unknown = set(scope) - set(SCOPE_KEYS)
    if unknown:
        errors.append(
            {"field": f"rules[{i}].scope", "message": f"Unknown key {sorted(unknown)[0]}."}
        )
        return
    for key, value in scope.items():
        if not exists[key](str(value)):
            errors.append({"field": f"rules[{i}].scope.{key}", "message": "Nothing with this id."})
            return
    # A rule can only switch payment on; the price comes from the resource type. When the
    # scope names one type or resource, a missing price is caught here, not at booking time.
    if rule.get("consequence") == "require_payment":
        for key in ("resourceTypeId", "resourceId"):
            if key in scope and not priced(key, str(scope[key])):
                errors.append(
                    {
                        "field": f"rules[{i}].consequence",
                        "message": "This resource type has no price "
                        "(flowConfig.payment.amountMinor), so there is nothing to charge.",
                    }
                )


def check_rules(
    rules: list[dict[str, Any]],
    *,
    site_exists: Callable[[str], bool],
    type_exists: Callable[[str], bool],
    resource_exists: Callable[[str], bool],
    priced: Callable[[str, str], bool],
) -> None:
    """Every check runs before anything is saved; errors are per field like custom fields.
    `priced(scope_key, id)`: does that resource type (or the resource's type) have a price?"""
    errors: list[dict[str, str]] = []
    seen: set[str] = set()
    exists = {"siteId": site_exists, "resourceTypeId": type_exists, "resourceId": resource_exists}
    if len(rules) > MAX_RULES:
        errors.append({"field": "rules", "message": f"At most {MAX_RULES} rules."})
    for i, rule in enumerate(rules):
        rid = rule.get("id", "")
        if not RULE_ID.match(str(rid)):
            errors.append({"field": f"rules[{i}].id", "message": "Use a-z, 0-9, - and _."})
        if rid in seen:
            errors.append({"field": f"rules[{i}].id", "message": "Duplicate rule id."})
        seen.add(rid)
        for gone, instead in (("stage", "consequence"), ("effect", "consequence and limit")):
            if gone in rule:
                errors.append(
                    {"field": f"rules[{i}].{gone}", "message": f"No longer used; use {instead}."}
                )
        if "enabled" in rule and not isinstance(rule["enabled"], bool):
            errors.append({"field": f"rules[{i}].enabled", "message": "Use true or false."})
        _check_scope(i, rule, errors, exists, priced)
        if rule.get("when") is not None:
            try:
                jsonlogic.check(rule["when"])
            except jsonlogic.JsonLogicError as exc:
                errors.append({"field": f"rules[{i}].when", "message": str(exc)})
        _check_consequence(i, rule, errors)
    if errors:
        raise ValidationFailed(errors)


@transaction.atomic
def publish(
    *,
    tenant_id: UUID,
    base_version: int,
    rules: list[dict[str, Any]],
    note: str | None,
    membership_id: UUID | None,
    site_exists: Callable[[str], bool],
    type_exists: Callable[[str], bool],
    resource_exists: Callable[[str], bool],
    priced: Callable[[str, str], bool],
) -> RuleSetVersion:
    """Replace the tenant's rules with a new version. Old versions stay for history and
    for bookings that were checked against them."""
    last = RuleSetVersion.objects.select_for_update().order_by("-version").first()
    current = last.version if last else 0
    if base_version != current:
        raise StaleVersion(
            f"This edit is based on rule set {base_version}; the current one is {current}."
        )
    check_rules(
        rules,
        site_exists=site_exists,
        type_exists=type_exists,
        resource_exists=resource_exists,
        priced=priced,
    )
    try:
        with transaction.atomic():
            row = RuleSetVersion.objects.create(
                tenant_id=tenant_id,
                version=current + 1,
                rules=rules,
                note=note,
                published_by_membership_id=membership_id,
            )
    except IntegrityError:  # two first publishes at once
        raise StaleVersion("Someone published rules at the same moment.") from None
    events.emit_event(
        tenant_id=tenant_id,
        name="config.published",
        subject_type="rule_set",
        subject_id=row.id,
        actor=events.user_actor(membership_id) if membership_id else events.SYSTEM,
        changes={"ruleSetVersion": {"from": current, "to": row.version}},
        config_versions={"ruleSet": row.version},
    )
    return row
