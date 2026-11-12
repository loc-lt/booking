"""Rules engine (docs/domain/rules.md). Pure: no database."""

import json
from pathlib import Path

import pytest

from modules.rules.engine import Rule, evaluate_rules
from modules.rules.jsonlogic import JsonLogicError, evaluate

EXAMPLE_RULE = Path(__file__).resolve().parents[3] / "docs" / "examples" / "rule.json"


@pytest.mark.parametrize(
    ("logic", "data", "expected"),
    [
        ({"==": [1, 1]}, {}, True),
        ({"==": [1, "1"]}, {}, True),
        ({"===": [1, "1"]}, {}, False),
        ({"var": "a.b"}, {"a": {"b": 3}}, 3),
        ({"var": ["missing", 7]}, {}, 7),
        ({"in": ["guest", {"var": "user.roles"}]}, {"user": {"roles": ["guest"]}}, True),
        ({"and": [True, []]}, {}, []),
        ({"or": [False, 0, "x"]}, {}, "x"),
        ({"!": [[]]}, {}, True),
        ({"<": [1, {"var": "x"}, 3]}, {"x": 2}, True),
        ({"if": [False, "a", True, "b", "c"]}, {}, "b"),
        (
            {">=": [{"var": "booking.durationMinutes"}, 120]},
            {"booking": {"durationMinutes": 90}},
            False,
        ),
        ({"missing": ["a", "b"]}, {"a": 1}, ["b"]),
    ],
)
def test_jsonlogic(logic, data, expected):
    assert evaluate(logic, data) == expected


def test_unknown_operator_raises():
    with pytest.raises(JsonLogicError):
        evaluate({"eval": ["import os"]}, {})


def _ctx(roles=("member",), minutes=60, days=1):
    return {
        "booking": {"durationMinutes": minutes, "startsInDays": days},
        "user": {"roles": list(roles)},
    }


def test_shared_example_rule():
    """docs/examples/rule.json: guests book at most 2 hours."""
    raw = json.loads(EXAMPLE_RULE.read_text())
    rule = Rule(
        id=raw["id"],
        scope="resource_type",
        when=raw["when"],
        consequence=raw["consequence"],
        limit=raw["limit"],
        priority=raw["priority"],
        message=raw["label"],
    )
    assert evaluate_rules([rule], _ctx(roles=["guest"], minutes=180)).denied == [
        {"ruleId": "guests-max-2h", "message": "Guests book at most 2 hours"}
    ]
    assert evaluate_rules([rule], _ctx(roles=["guest"], minutes=120)).allowed
    assert evaluate_rules([rule], _ctx(roles=["member"], minutes=180)).allowed


def test_deny_beats_allow_and_trace_names_every_rule():
    rules = [
        # "Only members may book", written as a deny on everyone else.
        Rule(
            "members-only",
            "tenant",
            {"!": [{"in": ["member", {"var": "user.roles"}]}]},
            "deny",
        ),
        Rule("weekend-off", "site", {"==": [1, 1]}, "deny", message="Closed"),
        Rule("never", "resource", {"==": [1, 2]}, "deny"),
    ]
    decision = evaluate_rules(rules, _ctx())
    assert decision.denied == [{"ruleId": "weekend-off", "message": "Closed"}]
    assert {t["ruleId"]: t["result"] for t in decision.trace} == {
        "members-only": "skipped",
        "weekend-off": "denied",
        "never": "skipped",
    }
    assert evaluate_rules(rules[:1], _ctx(roles=["guest"])).denied[0]["ruleId"] == "members-only"


def test_more_specific_scope_wins_for_limits():
    rules = [
        Rule("tenant-1h", "tenant", None, "deny", {"type": "max_duration", "minutes": 60}),
        Rule("room-4h", "resource", None, "deny", {"type": "max_duration", "minutes": 240}),
    ]
    # The room allows longer than the tenant: the room's limit applies.
    assert evaluate_rules(rules, _ctx(minutes=180)).allowed
    assert evaluate_rules(rules, _ctx(minutes=300)).denied[0]["ruleId"] == "room-4h"
    advance = [Rule("a-week", "tenant", None, "deny", {"type": "max_advance", "days": 7})]
    assert evaluate_rules(advance, _ctx(days=7)).allowed
    assert evaluate_rules(advance, _ctx(days=8)).denied[0]["ruleId"] == "a-week"


def test_quota_limit_counts_usage():
    rule = Rule(
        "two-a-day", "tenant", None, "deny", {"type": "quota", "per": "day", "maxBookings": 2}
    )
    ctx = {**_ctx(), "usage": {"day": {"bookings": 2, "minutes": 120}}}
    assert evaluate_rules([rule], ctx).denied[0]["ruleId"] == "two-a-day"
    ctx["usage"]["day"]["bookings"] = 1
    assert evaluate_rules([rule], ctx).allowed


def test_require_approval_require_payment_and_broken_conditions():
    rules = [
        Rule(
            "long-needs-approval",
            "resource_type",
            {">": [{"var": "booking.durationMinutes"}, 30]},
            "require_approval",
        ),
        Rule(
            "outsiders-pay",
            "tenant",
            {"!": [{"in": ["staff", {"var": "user.roles"}]}]},
            "require_payment",
        ),
    ]
    member = evaluate_rules(rules, _ctx(minutes=60))
    assert (member.require_approval, member.require_payment, member.allowed) == (True, True, True)
    staff = evaluate_rules(rules, _ctx(roles=["staff"], minutes=15))
    assert (staff.require_approval, staff.require_payment) == (False, False)
    broken = evaluate_rules([Rule("broken", "tenant", {"nope": [1]}, "require_approval")], _ctx())
    # A rule that can't be evaluated denies instead of silently allowing.
    assert broken.denied[0]["ruleId"] == "broken"
