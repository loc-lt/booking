"""Rules engine (docs/domain/rules.md). Pure: no database."""

import json
from pathlib import Path

import pytest

from modules.rules.engine import Rule, evaluate_stage
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
        ({"in": ["guest", {"var": "user.groups"}]}, {"user": {"groups": ["guest"]}}, True),
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


def _ctx(groups=("member",), minutes=60, days=1):
    return {
        "booking": {"durationMinutes": minutes, "startsInDays": days},
        "user": {"groups": list(groups)},
    }


def test_shared_example_rule():
    """docs/examples/rule.json: guests book at most 2 hours."""
    raw = json.loads(EXAMPLE_RULE.read_text())
    rule = Rule(
        id=raw["id"],
        stage=raw["stage"],
        scope="resource_type",
        when=raw["when"],
        effect=raw["effect"],
        priority=raw["priority"],
        message=raw["name"],
    )
    assert evaluate_stage([rule], "limits", _ctx(groups=["guest"], minutes=180)).denied == [
        {"ruleId": "guests-max-2h", "message": "Guests book at most 2 hours"}
    ]
    assert evaluate_stage([rule], "limits", _ctx(groups=["guest"], minutes=120)).allowed
    assert evaluate_stage([rule], "limits", _ctx(groups=["member"], minutes=180)).allowed


def test_deny_beats_allow_and_trace_names_every_rule():
    rules = [
        Rule(
            "allow-members",
            "eligibility",
            "tenant",
            None,
            {"type": "allowed_groups", "groups": ["member"]},
        ),
        Rule(
            "weekend-off", "eligibility", "site", {"==": [1, 1]}, {"type": "deny"}, message="Closed"
        ),
        Rule("never", "eligibility", "resource", {"==": [1, 2]}, {"type": "deny"}),
    ]
    decision = evaluate_stage(rules, "eligibility", _ctx())
    assert decision.denied == [{"ruleId": "weekend-off", "message": "Closed"}]
    assert {t["ruleId"]: t["result"] for t in decision.trace} == {
        "allow-members": "allowed",
        "weekend-off": "denied",
        "never": "skipped",
    }


def test_more_specific_scope_wins_for_limits():
    rules = [
        Rule("tenant-4h", "limits", "tenant", None, {"type": "max_duration", "minutes": 240}),
        Rule("room-1h", "limits", "resource", None, {"type": "max_duration", "minutes": 60}),
    ]
    assert evaluate_stage(rules, "limits", _ctx(minutes=90)).denied[0]["ruleId"] == "room-1h"
    assert evaluate_stage(rules, "limits", _ctx(minutes=60)).allowed


def test_require_approval_and_broken_conditions():
    rules = [
        Rule(
            "big-rooms",
            "approval",
            "resource_type",
            {">": [{"var": "booking.durationMinutes"}, 30]},
            {"type": "require_approval"},
        ),
        Rule("broken", "approval", "tenant", {"nope": [1]}, {"type": "require_approval"}),
    ]
    decision = evaluate_stage(rules, "approval", _ctx(minutes=60))
    assert decision.require_approval is True
    # A rule that can't be evaluated denies instead of silently allowing.
    assert decision.denied[0]["ruleId"] == "broken"
