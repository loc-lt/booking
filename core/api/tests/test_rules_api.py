"""Rules stored as versioned rule sets and applied by the pipeline (docs/domain/rules.md)."""

import json
from pathlib import Path

import pytest

from tests.conftest import book, create_resource, create_type, local

pytestmark = pytest.mark.django_db

EXAMPLE_RULE = Path(__file__).resolve().parents[3] / "docs" / "examples" / "rule.json"


def _publish(world, rules, base, role="owner"):
    return world.client(role).put(
        "/api/v1/rules", {"baseVersion": base, "rules": rules, "note": "test"}, format="json"
    )


@pytest.fixture
def room(world):
    rt = create_type(world, key="meeting_room")
    return create_resource(world, rt["id"])


def test_the_shared_example_rule_limits_guests(world, room, day):
    example = json.loads(EXAMPLE_RULE.read_text())
    published = _publish(world, [example], 0)
    assert published.status_code == 200, published.json()
    assert published.json()["version"] == 1
    denied = book(world, room["id"], local(day, 9), local(day, 12), role="guest")
    assert denied.status_code == 422
    assert denied.json()["reasons"] == [{"ruleId": "guests-max-2h", "message": example["name"]}]
    ok = book(world, room["id"], local(day, 9), local(day, 12), role="member")
    assert ok.status_code == 201
    assert ok.json()["appliedConfig"]["ruleSetVersion"] == 1


def test_publish_checks_every_rule_and_the_base_version(world, room):
    bad = _publish(
        world,
        [
            {"id": "Bad Id", "stage": "limits", "effect": {"type": "deny"}},
            {"id": "a", "stage": "approval", "effect": {"type": "max_duration", "minutes": 60}},
            {"id": "b", "stage": "eligibility", "when": {"eval": [1]}, "effect": {"type": "deny"}},
            {
                "id": "c",
                "stage": "limits",
                "scope": {"resourceType": "nope"},
                "effect": {"type": "deny"},
            },
            {"id": "d", "stage": "limits", "effect": {"type": "quota", "per": "month"}},
        ],
        0,
    )
    assert bad.status_code == 422
    fields = {e["field"] for e in bad.json()["errors"]}
    assert fields == {
        "rules[0].id",
        "rules[1].stage",
        "rules[2].when",
        "rules[3].scope.resourceType",
        "rules[4].effect.per",
        "rules[4].effect",
    }
    assert _publish(world, [], 0).json()["version"] == 1
    assert _publish(world, [], 0).status_code == 409  # someone published version 1 meanwhile
    assert _publish(world, [], 1, role="staff").status_code == 403
    versions = world.client("owner").get("/api/v1/rules/versions").json()["data"]
    assert [v["version"] for v in versions] == [1]


def test_approval_rule_sends_long_bookings_to_approval(world, room, day):
    _publish(
        world,
        [
            {
                "id": "long-needs-approval",
                "name": "Over 2 hours needs approval",
                "scope": {"siteId": str(world.site_id)},
                "stage": "approval",
                "when": {">": [{"var": "booking.durationMinutes"}, 120]},
                "effect": {"type": "require_approval"},
            }
        ],
        0,
    )
    assert book(world, room["id"], local(day, 9), local(day, 10)).json()["status"] == "confirmed"
    long = book(world, room["id"], local(day, 13), local(day, 16)).json()
    assert long["status"] == "pending_approval"
    # The decision is kept: approving later does not re-run today's rules.
    approved = world.client("staff").post(f"/api/v1/bookings/{long['id']}/approve")
    assert approved.json()["status"] == "confirmed"


def test_quota_counts_the_members_bookings(world, room, day):
    _publish(
        world,
        [
            {
                "id": "two-a-day",
                "stage": "limits",
                "effect": {"type": "quota", "per": "day", "maxBookings": 2},
                "message": "Two bookings a day",
            }
        ],
        0,
    )
    assert book(world, room["id"], local(day, 9), local(day, 10)).status_code == 201
    second = book(world, room["id"], local(day, 11), local(day, 12)).json()
    third = book(world, room["id"], local(day, 13), local(day, 14))
    assert third.json()["reasons"] == [{"ruleId": "two-a-day", "message": "Two bookings a day"}]
    # A cancelled booking no longer counts.
    world.client("member").post(f"/api/v1/bookings/{second['id']}/cancel")
    assert book(world, room["id"], local(day, 13), local(day, 14)).status_code == 201


def test_preview_runs_the_pipeline_without_saving(world, room, day):
    _publish(
        world,
        [
            {
                "id": "no-mornings-for-guests",
                "stage": "eligibility",
                "when": {
                    "and": [
                        {"in": ["guest", {"var": "user.groups"}]},
                        {"<": [{"var": "time.hour"}, 12]},
                    ]
                },
                "effect": {"type": "deny"},
                "message": "Guests book afternoons only",
            }
        ],
        0,
    )
    body = {
        "resourceId": room["id"],
        "start": local(day, 9).isoformat(),
        "end": local(day, 10).isoformat(),
    }
    guest = world.client("guest").post("/api/v1/bookings/preview", body, format="json").json()
    assert guest["allowed"] is False
    assert guest["reasons"][0]["ruleId"] == "no-mornings-for-guests"
    assert guest["trace"] == [
        {
            "stage": "eligibility",
            "ruleId": "no-mornings-for-guests",
            "matched": True,
            "result": "denied",
        }
    ]
    member = world.client("member").post("/api/v1/bookings/preview", body, format="json").json()
    assert (member["allowed"], member["status"], member["slotFree"]) == (True, "confirmed", True)
    assert member["appliedConfig"]["ruleSetVersion"] == 1
    assert world.client("member").get("/api/v1/bookings").json()["data"] == []
    book(world, room["id"], local(day, 9), local(day, 10), role="member2")
    taken = world.client("member").post("/api/v1/bookings/preview", body, format="json").json()
    assert (taken["allowed"], taken["slotFree"]) == (False, False)


def test_rules_of_another_scope_do_not_apply(world, room, day):
    other = create_resource(world, create_type(world, key="desk")["id"], label="Desk 1")
    _publish(
        world,
        [
            {
                "id": "desks-closed",
                "scope": {"resourceType": "desk"},
                "stage": "eligibility",
                "effect": {"type": "deny"},
            },
            {
                "id": "room-only-staff",
                "scope": {"resourceId": room["id"]},
                "stage": "eligibility",
                "effect": {"type": "allowed_groups", "groups": ["staff", "owner"]},
            },
        ],
        0,
    )
    assert (
        book(world, other["id"], local(day, 9), local(day, 10)).json()["reasons"][0]["ruleId"]
        == "desks-closed"
    )
    assert (
        book(world, room["id"], local(day, 9), local(day, 10)).json()["reasons"][0]["ruleId"]
        == "room-only-staff"
    )
    assert book(world, room["id"], local(day, 9), local(day, 10), role="staff").status_code == 201
