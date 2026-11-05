"""Public interface of the rules module: storing, publishing and applying booking rules.

A tenant's rules are one rule set with a version. Publishing replaces the whole set (with
baseVersion, like policies), so a booking can always name the exact rules it was checked
against. The rule shape is docs/examples/rule.json:

  {"id": "guests-max-2h", "name": "...", "scope": {"resourceType": "meeting_room"},
   "stage": "limits", "priority": 10, "when": <JSONLogic>, "effect": {...}}

scope: {} (whole tenant) | {"siteId"} | {"resourceType": key} | {"resourceId"}.
"""

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction

from kernel.errors import StaleVersion, ValidationFailed
from modules.events import service as events
from modules.rules import jsonlogic
from modules.rules.engine import MAX_RULES_PER_STAGE, STAGES, Decision, Rule, evaluate_stage
from modules.rules.models import RuleSetVersion

RULE_SET_VERSION_NONE = 0
RULE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")

# effect type -> (stages it may be used in, required keys)
EFFECTS: dict[str, tuple[frozenset[str], tuple[str, ...]]] = {
    "deny": (frozenset(STAGES), ()),
    "allowed_groups": (frozenset({"eligibility"}), ("groups",)),
    "max_duration": (frozenset({"limits"}), ("minutes",)),
    "advance_window": (frozenset({"limits"}), ("days",)),
    "quota": (frozenset({"limits"}), ("per",)),
    "require_approval": (frozenset({"approval"}), ()),
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
    if "resourceType" in scope:
        return "resource_type"
    if "siteId" in scope:
        return "site"
    return "tenant"


def _applies(
    scope: dict[str, Any], location_id: UUID, resource_type_key: str, resource_id: UUID
) -> bool:
    kind = _scope_kind(scope)
    if kind == "resource":
        return scope["resourceId"] == str(resource_id)
    if kind == "resource_type":
        return scope["resourceType"] == resource_type_key
    if kind == "site":
        return scope["siteId"] == str(location_id)
    return True


def published_rules(
    *, location_id: UUID, resource_type_key: str, resource_id: UUID
) -> tuple[list[Rule], int]:
    """(rules for this booking's scope, most general first; rule set version)."""
    version, raw, _ = current_rule_set()
    picked = [
        r
        for r in raw
        if r.get("enabled", True)
        and _applies(r.get("scope") or {}, location_id, resource_type_key, resource_id)
    ]
    rules = [to_engine(r, version) for r in picked]
    order = {"tenant": 0, "site": 1, "resource_type": 2, "resource": 3}
    return sorted(rules, key=lambda r: order[r.scope]), version


def to_engine(raw: dict[str, Any], version: int = 1) -> Rule:
    return Rule(
        id=raw["id"],
        stage=raw["stage"],
        scope=_scope_kind(raw.get("scope") or {}),
        when=raw.get("when"),
        effect=raw["effect"],
        priority=int(raw.get("priority", 0)),
        message=raw.get("message") or raw.get("name"),
        version=version,
    )


def decide(rules: list[Rule], stage: str, context: dict[str, Any]) -> Decision:
    return evaluate_stage(rules, stage, context)


# ---------- publishing ----------


def _check_effect(i: int, rule: dict[str, Any], errors: list[dict[str, str]]) -> None:
    def err(name: str, message: str) -> None:
        errors.append({"field": f"rules[{i}].{name}", "message": message})

    effect = rule.get("effect")
    if not isinstance(effect, dict) or effect.get("type") not in EFFECTS:
        err("effect.type", f"Use one of: {', '.join(sorted(EFFECTS))}.")
        return
    stages, required = EFFECTS[effect["type"]]
    if rule.get("stage") not in stages:
        err("stage", f"Effect {effect['type']} works in: {', '.join(sorted(stages))}.")
    for key in required:
        if key not in effect:
            err(f"effect.{key}", "Required for this effect.")
    kind = effect["type"]
    for key in ("minutes", "days", "maxBookings", "maxMinutes"):
        if key in effect and (not isinstance(effect[key], int) or effect[key] < 0):
            err(f"effect.{key}", "Use a whole number, 0 or more.")
    if kind == "quota":
        if effect.get("per") not in ("day", "week"):
            err("effect.per", "Use day or week.")
        if "maxBookings" not in effect and "maxMinutes" not in effect:
            err("effect", "A quota needs maxBookings or maxMinutes.")
    if kind == "allowed_groups" and (
        not isinstance(effect.get("groups"), list)
        or not all(isinstance(g, str) for g in effect["groups"])
    ):
        err("effect.groups", "A list of role codes.")


def check_rules(
    rules: list[dict[str, Any]],
    *,
    site_exists: Callable[[str], bool],
    type_key_exists: Callable[[str], bool],
    resource_exists: Callable[[str], bool],
) -> None:
    """Every check runs before anything is saved; errors are per field like custom fields."""
    errors: list[dict[str, str]] = []
    seen: set[str] = set()
    per_stage: dict[str, int] = {}
    for i, rule in enumerate(rules):
        rid = rule.get("id", "")
        if not RULE_ID.match(str(rid)):
            errors.append({"field": f"rules[{i}].id", "message": "Use a-z, 0-9, - and _."})
        if rid in seen:
            errors.append({"field": f"rules[{i}].id", "message": "Duplicate rule id."})
        seen.add(rid)
        stage = rule.get("stage")
        if stage not in STAGES:
            errors.append(
                {"field": f"rules[{i}].stage", "message": f"Use one of: {', '.join(STAGES)}."}
            )
        else:
            per_stage[stage] = per_stage.get(stage, 0) + 1
        scope = rule.get("scope") or {}
        if not isinstance(scope, dict) or len(scope) > 1:
            errors.append(
                {
                    "field": f"rules[{i}].scope",
                    "message": "Empty (whole tenant) or one of siteId, resourceType, resourceId.",
                }
            )
        else:
            for key, exists in (
                ("siteId", site_exists),
                ("resourceType", type_key_exists),
                ("resourceId", resource_exists),
            ):
                if key in scope and not exists(str(scope[key])):
                    errors.append(
                        {"field": f"rules[{i}].scope.{key}", "message": "Nothing with this id."}
                    )
            unknown = set(scope) - {"siteId", "resourceType", "resourceId"}
            if unknown:
                errors.append(
                    {"field": f"rules[{i}].scope", "message": f"Unknown key {sorted(unknown)[0]}."}
                )
        if rule.get("when") is not None:
            try:
                jsonlogic.check(rule["when"])
            except jsonlogic.JsonLogicError as exc:
                errors.append({"field": f"rules[{i}].when", "message": str(exc)})
        _check_effect(i, rule, errors)
    for stage, count in per_stage.items():
        if count > MAX_RULES_PER_STAGE:
            errors.append(
                {"field": "rules", "message": f"At most {MAX_RULES_PER_STAGE} rules in {stage}."}
            )
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
    type_key_exists: Callable[[str], bool],
    resource_exists: Callable[[str], bool],
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
        type_key_exists=type_key_exists,
        resource_exists=resource_exists,
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
