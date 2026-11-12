"""Rule evaluation (docs/domain/rules.md). Pure functions: no database, no clock.

A rule is scope + condition (`when`, JSONLogic) + consequence + priority, with an optional
`limit` on deny rules.
1. Rules arrive most general first: tenant -> site -> resource type -> resource.
2. The context has fixed keys: booking, resource, user, user.roles, time, usage.
3. Every rule's condition is evaluated in one pass, highest priority first.
4. Consequences: any matching deny blocks (deny beats allow); require_approval and
   require_payment are ORed. For max_duration and max_advance limits the more specific scope
   wins, so a room can allow longer than the tenant-wide limit.
5. The result carries a trace naming every rule that ran and what it did.
"""

from dataclasses import dataclass, field
from typing import Any

from modules.rules.jsonlogic import JsonLogicError, evaluate, truthy

CONSEQUENCES = ("deny", "require_approval", "require_payment")
LIMITS = ("max_duration", "max_advance", "quota")
SCOPE_ORDER = {"tenant": 0, "site": 1, "resource_type": 2, "resource": 3}
MAX_RULES = 200  # same as PublishRulesRequest.rules maxItems in the contract


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    scope: str  # tenant | site | resource_type | resource
    when: Any
    consequence: str
    limit: dict[str, Any] | None = None
    priority: int = 0
    message: str | None = None
    version: int = 1


@dataclass(slots=True)
class Decision:
    denied: list[dict[str, str]] = field(default_factory=list)  # [{ruleId, message}]
    require_approval: bool = False
    require_payment: bool = False
    trace: list[dict[str, Any]] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return not self.denied


def _ordered(rules: list[Rule]) -> list[Rule]:
    if len(rules) > MAX_RULES:
        raise ValueError(f"More than {MAX_RULES} rules apply.")
    # Highest priority first; on equal priority, the more specific scope first.
    return sorted(rules, key=lambda r: (-r.priority, -SCOPE_ORDER[r.scope]))


def _deny(decision: Decision, rule: Rule, fallback: str) -> None:
    decision.denied.append({"ruleId": rule.id, "message": rule.message or fallback})


def _apply(rule: Rule, ctx: dict[str, Any], decision: Decision, limits: dict[str, Rule]) -> str:
    """Apply one matched rule's consequence. Returns what happened, for the trace."""
    if rule.consequence == "require_approval":
        decision.require_approval = True
        return "approval required"
    if rule.consequence == "require_payment":
        decision.require_payment = True
        return "payment required"
    if rule.consequence != "deny":
        raise ValueError(f"Unknown consequence {rule.consequence!r} in rule {rule.id}")
    kind = (rule.limit or {}).get("type")
    if kind is None:
        _deny(decision, rule, "Not allowed.")
        return "denied"
    if kind in ("max_duration", "max_advance"):
        # Ties go to the more specific scope: keep the most specific rule per limit.
        current = limits.get(kind)
        if current is None or SCOPE_ORDER[rule.scope] > SCOPE_ORDER[current.scope]:
            limits[kind] = rule
        return "limit noted"
    if kind == "quota":
        return _check_quota(rule, ctx, decision)
    raise ValueError(f"Unknown limit {kind!r} in rule {rule.id}")


def _check_quota(rule: Rule, ctx: dict[str, Any], decision: Decision) -> str:
    """limit {type: quota, per: day|week, maxBookings?, maxMinutes?}. ctx.usage holds what the
    member already has in that period (open and completed bookings), without this one."""
    limit = rule.limit or {}
    per = limit.get("per", "day")
    used = ctx.get("usage", {}).get(per, {"bookings": 0, "minutes": 0})
    minutes = ctx.get("booking", {}).get("durationMinutes", 0)
    max_bookings = limit.get("maxBookings")
    max_minutes = limit.get("maxMinutes")
    if max_bookings is not None and used["bookings"] + 1 > max_bookings:
        _deny(decision, rule, f"At most {max_bookings} bookings per {per}.")
        return "denied: booking quota reached"
    if max_minutes is not None and used["minutes"] + minutes > max_minutes:
        _deny(decision, rule, f"At most {max_minutes} minutes per {per}.")
        return "denied: minute quota reached"
    return "within quota"


def _check_limits(limits: dict[str, Rule], ctx: dict[str, Any], decision: Decision) -> None:
    booking = ctx.get("booking", {})
    for kind, measured, unit, text in (
        ("max_duration", "durationMinutes", "minutes", "At most {} minutes."),
        ("max_advance", "startsInDays", "days", "At most {} days ahead."),
    ):
        rule = limits.get(kind)
        if rule is None:
            continue
        bound = (rule.limit or {})[unit]
        if booking.get(measured, 0) > bound:
            _deny(decision, rule, text.format(bound))


def evaluate_rules(rules: list[Rule], ctx: dict[str, Any]) -> Decision:
    decision = Decision()
    limits: dict[str, Rule] = {}
    for rule in _ordered(rules):
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
