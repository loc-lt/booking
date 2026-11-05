"""policy_versions.body: the engine's view of a resource type's policies.

The contract exposes it as `flowConfig`. confirmation, checkIn and cancellation are required;
limits, buffers and payment are optional sections: when a request leaves one out, its keys
are copied unchanged from the previous version (or the platform defaults).

Mapping (docs/database/API_KICH_BAN.md 8.2), units in the body are seconds:
  confirmation: instant|approval            <-> requires_approval
  checkIn.required                          <-> checkin_required
  checkIn.opensMinutesBefore                <-> checkin_open_before_seconds / 60
  checkIn.noShowAfterMinutes                <-> no_show_after_seconds / 60
  cancellation.allowedUntilMinutesBefore    <-> cancel_allowed_until_seconds / 60
  limits.minDurationMinutes                 <-> min_duration_seconds / 60
  limits.maxDurationMinutes                 <-> max_duration_seconds / 60
  limits.leadTimeMinutes                    <-> lead_time_min_seconds / 60
  limits.bookingWindowDays                  <-> booking_window_days
  buffers.beforeMinutes / afterMinutes      <-> buffer_before_seconds / buffer_after_seconds
  payment.mode: none|upfront                <-> requires_payment
  payment.amountMinor, payment.per          <-> price {amount_minor, per}
  payment.holdMinutes                       <-> hold_ttl_seconds / 60
  payment.refundRules[{minutesBefore, percent}] <-> refund_rules[{before_seconds, percent}]
"""

from typing import Any

from jsonschema import Draft202012Validator

from kernel.errors import ValidationFailed

_NON_NEGATIVE_INT = {"type": "integer", "minimum": 0}

BODY_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "requires_approval",
        "requires_payment",
        "checkin_required",
        "checkin_open_before_seconds",
        "no_show_after_seconds",
        "cancel_allowed_until_seconds",
        "hold_ttl_seconds",
        "min_duration_seconds",
        "max_duration_seconds",
        "lead_time_min_seconds",
        "booking_window_days",
        "buffer_before_seconds",
        "buffer_after_seconds",
    ],
    "properties": {
        "requires_approval": {"type": "boolean"},
        "requires_payment": {"type": "boolean"},
        "price": {
            "type": "object",
            "additionalProperties": False,
            "required": ["amount_minor", "per"],
            "properties": {
                "amount_minor": _NON_NEGATIVE_INT,
                "per": {"enum": ["booking", "hour"]},
            },
        },
        "refund_rules": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["before_seconds", "percent"],
                "properties": {
                    "before_seconds": _NON_NEGATIVE_INT,
                    "percent": {"type": "integer", "minimum": 0, "maximum": 100},
                },
            },
        },
        "checkin_required": {"type": "boolean"},
        "checkin_open_before_seconds": _NON_NEGATIVE_INT,
        "no_show_after_seconds": _NON_NEGATIVE_INT,
        "cancel_allowed_until_seconds": _NON_NEGATIVE_INT,
        "hold_ttl_seconds": {"type": "integer", "minimum": 60},
        "min_duration_seconds": _NON_NEGATIVE_INT,
        "max_duration_seconds": {"type": "integer", "minimum": 60},
        "lead_time_min_seconds": _NON_NEGATIVE_INT,
        "booking_window_days": {"type": "integer", "minimum": 1, "maximum": 730},
        "buffer_before_seconds": _NON_NEGATIVE_INT,
        "buffer_after_seconds": _NON_NEGATIVE_INT,
    },
}
_validator = Draft202012Validator(BODY_SCHEMA)

DEFAULT_BODY: dict[str, Any] = {
    "requires_approval": False,
    "requires_payment": False,
    "price": {"amount_minor": 0, "per": "booking"},
    "refund_rules": [],
    "checkin_required": False,
    "checkin_open_before_seconds": 900,
    "no_show_after_seconds": 900,
    "cancel_allowed_until_seconds": 0,
    "hold_ttl_seconds": 600,
    "min_duration_seconds": 0,
    "max_duration_seconds": 8 * 3600,
    "lead_time_min_seconds": 0,
    "booking_window_days": 90,
    "buffer_before_seconds": 0,
    "buffer_after_seconds": 0,
}


def validate_body(body: dict[str, Any]) -> None:
    """JSON Schema first, then cross-key checks (docs/domain/configuration.md, "Validate")."""
    errors = [{"field": "flowConfig", "message": e.message} for e in _validator.iter_errors(body)]
    if errors:
        raise ValidationFailed(errors)
    if body["min_duration_seconds"] > body["max_duration_seconds"]:
        raise ValidationFailed.one(
            "flowConfig.limits.minDurationMinutes", "Minimum duration is longer than the maximum."
        )
    if body["requires_payment"] and body["price"]["amount_minor"] <= 0:
        raise ValidationFailed.one(
            "flowConfig.payment.amountMinor", "An upfront payment needs a price above 0."
        )


def body_from_flow_config(
    flow: dict[str, Any], base: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Apply a contract flowConfig onto a body; every key it leaves out is copied from
    `base` (the previous version), else from DEFAULT_BODY."""
    body = {**DEFAULT_BODY, **(base or {})}
    check_in = flow["checkIn"]
    body.update(
        requires_approval=flow["confirmation"] == "approval",
        checkin_required=bool(check_in["required"]),
        checkin_open_before_seconds=int(check_in["opensMinutesBefore"]) * 60,
        no_show_after_seconds=int(check_in["noShowAfterMinutes"]) * 60,
        cancel_allowed_until_seconds=int(flow["cancellation"]["allowedUntilMinutesBefore"]) * 60,
    )
    limits = flow.get("limits")
    if limits:
        for src, dst, factor in (
            ("minDurationMinutes", "min_duration_seconds", 60),
            ("maxDurationMinutes", "max_duration_seconds", 60),
            ("leadTimeMinutes", "lead_time_min_seconds", 60),
            ("bookingWindowDays", "booking_window_days", 1),
        ):
            if src in limits:
                body[dst] = int(limits[src]) * factor
    buffers = flow.get("buffers")
    if buffers:
        if "beforeMinutes" in buffers:
            body["buffer_before_seconds"] = int(buffers["beforeMinutes"]) * 60
        if "afterMinutes" in buffers:
            body["buffer_after_seconds"] = int(buffers["afterMinutes"]) * 60
    payment = flow.get("payment")
    if payment:
        body["requires_payment"] = payment["mode"] == "upfront"
        price = dict(body.get("price") or DEFAULT_BODY["price"])
        if "amountMinor" in payment:
            price["amount_minor"] = int(payment["amountMinor"])
        if "per" in payment:
            price["per"] = payment["per"]
        body["price"] = price
        if "holdMinutes" in payment:
            body["hold_ttl_seconds"] = int(payment["holdMinutes"]) * 60
        if "refundRules" in payment:
            body["refund_rules"] = sorted(
                (
                    {"before_seconds": int(r["minutesBefore"]) * 60, "percent": int(r["percent"])}
                    for r in payment["refundRules"]
                ),
                key=lambda r: -r["before_seconds"],
            )
    return body


def flow_config_from_body(body: dict[str, Any]) -> dict[str, Any]:
    body = {**DEFAULT_BODY, **body}
    price = body["price"] or DEFAULT_BODY["price"]
    return {
        "confirmation": "approval" if body["requires_approval"] else "instant",
        "checkIn": {
            "required": body["checkin_required"],
            "opensMinutesBefore": body["checkin_open_before_seconds"] // 60,
            "noShowAfterMinutes": body["no_show_after_seconds"] // 60,
        },
        "cancellation": {
            "allowedUntilMinutesBefore": body["cancel_allowed_until_seconds"] // 60,
        },
        "limits": {
            "minDurationMinutes": body["min_duration_seconds"] // 60,
            "maxDurationMinutes": body["max_duration_seconds"] // 60,
            "leadTimeMinutes": body["lead_time_min_seconds"] // 60,
            "bookingWindowDays": body["booking_window_days"],
        },
        "buffers": {
            "beforeMinutes": body["buffer_before_seconds"] // 60,
            "afterMinutes": body["buffer_after_seconds"] // 60,
        },
        "payment": {
            "mode": "upfront" if body["requires_payment"] else "none",
            "amountMinor": price["amount_minor"],
            "per": price["per"],
            "holdMinutes": body["hold_ttl_seconds"] // 60,
            "refundRules": [
                {"minutesBefore": r["before_seconds"] // 60, "percent": r["percent"]}
                for r in body["refund_rules"]
            ],
        },
    }


def refund_percent(body: dict[str, Any], seconds_before_start: float) -> int:
    """Share of the amount refunded when cancelling this long before the start. No rules ->
    100%. Rules are sorted by before_seconds, largest first; the first one met applies."""
    rules = body.get("refund_rules") or []
    if not rules:
        return 100
    for rule in rules:
        if seconds_before_start >= rule["before_seconds"]:
            return int(rule["percent"])
    return 0
