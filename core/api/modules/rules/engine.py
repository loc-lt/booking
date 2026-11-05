"""Rule evaluation (docs/domain/rules.md). Pure functions: no database, no clock.

A rule is scope + stage + condition (`when`, JSONLogic) + effect + priority.
1. Rules arrive most general first: tenant -> site -> resource type -> resource.
2. The context has fixed keys: booking, resource, user, user.groups, time, usage.
3. For one stage, each rule's condition is evaluated, highest priority first.
4. Conflicts: deny beats allow; for limits, the more specific scope wins.
5. The result carries a trace naming every rule that matched and what it did.
"""

from dataclasses import dataclass, field
from typing import Any

from modules.rules.jsonlogic import JsonLogicError, evaluate, truthy

STAGES = ("eligibility", "limits", "approval")
SCOPE_ORDER = {"tenant": 0, "site": 1, "resource_type": 2, "resource": 3}
MAX_RULES_PER_STAGE = 50


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    stage: str
    scope: str  # tenant | site | resource_type | resource
    when: Any
    effect: dict[str, Any]
    priority: int = 0
    message: str | None = None
    version: int = 1


@dataclass(slots=True)
class Decision:
    denied: list[dict[str, str]] = field(default_factory=list)  # [{ruleId, message}]
    require_approval: bool = False
    trace: list[dict[str, Any]] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return not self.denied


def _ordered(rules: list[Rule], stage: str) -> list[Rule]:
    picked = [r for r in rules if r.stage == stage]
    if len(picked) > MAX_RULES_PER_STAGE:
        raise ValueError(f"More than {MAX_RULES_PER_STAGE} rules in stage {stage}.")
    # Highest priority first; on equal priority, the more specific scope first.
    return sorted(picked, key=lambda r: (-r.priority, -SCOPE_ORDER[r.scope]))


def _apply(rule: Rule, ctx: dict[str, Any], decision: Decision, limits: dict[str, Rule]) -> str:
    """Apply one matched rule's effect. Returns what happened, for the trace."""
    effect = rule.effect
    kind = effect.get("type")
    if kind == "deny":
        decision.denied.append({"ruleId": rule.id, "message": rule.message or "Not allowed."})
        return "denied"
    if kind == "require_approval":
        decision.require_approval = True
        return "approval required"
    if kind == "allowed_groups":
        groups = set(ctx.get("user", {}).get("groups", []))
        if groups.isdisjoint(effect.get("groups", [])):
            decision.denied.append(
                {"ruleId": rule.id, "message": rule.message or "Your group can't book this."}
            )
            return "denied: group not allowed"
        return "allowed"
    if kind in ("max_duration", "advance_window"):
        # Ties go to the more specific scope: keep the most specific rule per limit.
        current = limits.get(kind)
        if current is None or SCOPE_ORDER[rule.scope] > SCOPE_ORDER[current.scope]:
            limits[kind] = rule
        return "limit noted"
    if kind == "quota":
        return _check_quota(rule, ctx, decision)
    raise ValueError(f"Unknown effect {kind!r} in rule {rule.id}")


def _check_quota(rule: Rule, ctx: dict[str, Any], decision: Decision) -> str:
    """effect {type: quota, per: day|week, maxBookings?, maxMinutes?}. ctx.usage holds what the
    member already has in that period (open and completed bookings), without this one."""
    per = rule.effect.get("per", "day")
    used = ctx.get("usage", {}).get(per, {"bookings": 0, "minutes": 0})
    minutes = ctx.get("booking", {}).get("durationMinutes", 0)
    max_bookings = rule.effect.get("maxBookings")
    max_minutes = rule.effect.get("maxMinutes")
    if max_bookings is not None and used["bookings"] + 1 > max_bookings:
        decision.denied.append(
            {
                "ruleId": rule.id,
                "message": rule.message or f"At most {max_bookings} bookings per {per}.",
            }
        )
        return "denied: booking quota reached"
    if max_minutes is not None and used["minutes"] + minutes > max_minutes:
        decision.denied.append(
            {
                "ruleId": rule.id,
                "message": rule.message or f"At most {max_minutes} minutes per {per}.",
            }
        )
        return "denied: minute quota reached"
    return "within quota"


def _check_limits(limits: dict[str, Rule], ctx: dict[str, Any], decision: Decision) -> None:
    booking = ctx.get("booking", {})
    rule = limits.get("max_duration")
    if rule and booking.get("durationMinutes", 0) > rule.effect["minutes"]:
        decision.denied.append(
            {
                "ruleId": rule.id,
                "message": rule.message or f"At most {rule.effect['minutes']} minutes.",
            }
        )
    rule = limits.get("advance_window")
    if rule and booking.get("startsInDays", 0) > rule.effect["days"]:
        decision.denied.append(
            {
                "ruleId": rule.id,
                "message": rule.message or f"At most {rule.effect['days']} days ahead.",
            }
        )


def evaluate_stage(rules: list[Rule], stage: str, ctx: dict[str, Any]) -> Decision:
    if stage not in STAGES:
        raise ValueError(f"Unknown stage {stage}")
    decision = Decision()
    limits: dict[str, Rule] = {}
    for rule in _ordered(rules, stage):
        try:
            matched = truthy(evaluate(rule.when, ctx)) if rule.when is not None else True
        except JsonLogicError as exc:
            # A broken condition denies rather than silently allowing.
            decision.denied.append(
                {"ruleId": rule.id, "message": "This rule could not be checked."}
            )
            decision.trace.append({"ruleId": rule.id, "matched": None, "result": f"error: {exc}"})
            continue
        if not matched:
            decision.trace.append({"ruleId": rule.id, "matched": False, "result": "skipped"})
            continue
        result = _apply(rule, ctx, decision, limits)
        decision.trace.append({"ruleId": rule.id, "matched": True, "result": result})
    _check_limits(limits, ctx, decision)
    return decision
