"""Rules stored as versioned rule sets and applied by the pipeline (docs/domain/rules.md)."""

import json
from pathlib import Path

import pytest

from tests.conftest import FLOW_INSTANT, book, create_resource, create_type, local

pytestmark = pytest.mark.django_db

EXAMPLE_RULE = Path(__file__).resolve().parents[3] / "docs" / "examples" / "rule.json"

# Free by default (mode none), but with a price a require_payment rule can charge.
PRICED_FREE_FLOW = {
    **FLOW_INSTANT,
    "payment": {"mode": "none", "amountMinor": 50000, "per": "booking", "holdMinutes": 15},
}


def _publish(world, rules, base, role="owner"):
    return world.client(role).put(
        "/api/v1/rules", {"baseVersion": base, "rules": rules, "note": "test"}, format="json"
    )


@pytest.fixture
def room_type(world):
    return create_type(world, key="meeting_room")


@pytest.fixture
def room(world, room_type):
    return create_resource(world, room_type["id"])


def test_the_shared_example_rule_limits_guests(world, room_type, room, day):
    example = json.loads(EXAMPLE_RULE.read_text())
    example["scope"] = {"resourceTypeId": room_type["id"]}
    published = _publish(world, [example], 0)
    assert published.status_code == 200, published.json()
    assert published.json()["version"] == 1
    assert published.json()["rules"] == [example]
    denied = book(world, room["id"], local(day, 9), local(day, 12), role="guest")
    assert denied.status_code == 422
    assert denied.json()["reasons"] == [{"ruleId": "guests-max-2h", "message": example["label"]}]
    ok = book(world, room["id"], local(day, 9), local(day, 12), role="member")
    assert ok.status_code == 201
    assert ok.json()["appliedConfig"]["ruleSetVersion"] == 1


def test_publish_checks_every_rule_and_the_base_version(world, room):
    bad = _publish(
        world,
        [
            {"id": "Bad Id", "consequence": "deny"},
            {"id": "a", "consequence": "require_approval", "limit": {"type": "quota"}},
            {"id": "b", "when": {"eval": [1]}, "consequence": "deny"},
            {
                "id": "c",
                "scope": {"resourceTypeId": "0193f4c4-2d6e-7f6b-ba5d-4c2e9f8a7b6c"},
                "consequence": "deny",
            },
            {"id": "d", "consequence": "deny", "limit": {"type": "quota", "per": "month"}},
            {"id": "e", "stage": "limits", "effect": {"type": "deny"}},
            {"id": "f", "consequence": "deny", "limit": {"type": "max_duration"}},
        ],
        0,
    )
    assert bad.status_code == 422
    fields = {e["field"] for e in bad.json()["errors"]}
    assert fields == {
        "rules[0].id",
        "rules[1].limit",
        "rules[2].when",
        "rules[3].scope.resourceTypeId",
        "rules[4].limit.per",
        "rules[4].limit",
        "rules[5].stage",
        "rules[5].effect",
        "rules[5].consequence",
        "rules[6].limit.minutes",
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
                "label": "Over 2 hours needs approval",
                "scope": {"siteId": str(world.site_id)},
                "when": {">": [{"var": "booking.durationMinutes"}, 120]},
                "consequence": "require_approval",
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
                "consequence": "deny",
                "limit": {"type": "quota", "per": "day", "maxBookings": 2},
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


def test_a_disabled_rule_does_not_apply(world, room, day):
    rule = {"id": "closed", "consequence": "deny", "enabled": False}
    assert _publish(world, [rule], 0).status_code == 200
    assert book(world, room["id"], local(day, 9), local(day, 10)).status_code == 201
    assert _publish(world, [{**rule, "enabled": "no"}], 1).status_code == 422


def test_preview_runs_the_pipeline_without_saving(world, room, day):
    _publish(
        world,
        [
            {
                "id": "no-mornings-for-guests",
                "when": {
                    "and": [
                        {"in": ["guest", {"var": "user.roles"}]},
                        {"<": [{"var": "time.hour"}, 12]},
                    ]
                },
                "consequence": "deny",
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
        {"ruleId": "no-mornings-for-guests", "matched": True, "result": "denied"}
    ]
    member = world.client("member").post("/api/v1/bookings/preview", body, format="json").json()
    assert (member["allowed"], member["status"], member["slotFree"]) == (True, "confirmed", True)
    assert member["appliedConfig"]["ruleSetVersion"] == 1
    assert world.client("member").get("/api/v1/bookings").json()["data"] == []
    book(world, room["id"], local(day, 9), local(day, 10), role="member2")
    taken = world.client("member").post("/api/v1/bookings/preview", body, format="json").json()
    assert (taken["allowed"], taken["slotFree"]) == (False, False)


def test_rules_of_another_scope_do_not_apply(world, room, day):
    desk_type = create_type(world, key="desk")
    other = create_resource(world, desk_type["id"], label="Desk 1")
    _publish(
        world,
        [
            {
                "id": "desks-closed",
                "scope": {"resourceTypeId": desk_type["id"]},
                "consequence": "deny",
            },
            {
                # "Only staff and owners", written as a deny on everyone else.
                "id": "room-only-staff",
                "scope": {"resourceId": room["id"]},
                "when": {
                    "!": [
                        {
                            "or": [
                                {"in": ["staff", {"var": "user.roles"}]},
                                {"in": ["owner", {"var": "user.roles"}]},
                            ]
                        }
                    ]
                },
                "consequence": "deny",
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


def test_a_more_specific_limit_overrides_the_tenant_one(world, room, day):
    _publish(
        world,
        [
            {
                "id": "tenant-1h",
                "consequence": "deny",
                "limit": {"type": "max_duration", "minutes": 60},
            },
            {
                "id": "room-3h",
                "scope": {"resourceId": room["id"]},
                "consequence": "deny",
                "limit": {"type": "max_duration", "minutes": 180},
            },
        ],
        0,
    )
    assert book(world, room["id"], local(day, 9), local(day, 11)).status_code == 201
    over = book(world, room["id"], local(day, 13), local(day, 17))
    assert over.json()["reasons"][0]["ruleId"] == "room-3h"


def test_require_payment_rule_charges_the_types_price(world, day):
    studio = create_type(world, key="studio", flowConfig=PRICED_FREE_FLOW)
    room = create_resource(world, studio["id"], label="Studio 1")
    rule = {
        "id": "outsiders-pay",
        "label": "Anyone not on staff pays",
        "scope": {"resourceTypeId": studio["id"]},
        "when": {"!": [{"in": ["staff", {"var": "user.roles"}]}]},
        "consequence": "require_payment",
    }
    assert _publish(world, [rule], 0).status_code == 200
    member = book(world, room["id"], local(day, 9), local(day, 10)).json()
    assert member["status"] == "awaiting_payment"
    assert (member["payment"]["status"], member["payment"]["amountMinor"]) == ("pending", 50000)
    staff = book(world, room["id"], local(day, 11), local(day, 12), role="staff").json()
    assert staff["status"] == "confirmed"


def test_require_payment_on_a_type_without_price_is_rejected_at_publish(world, room_type):
    bad = _publish(
        world,
        [
            {
                "id": "pay",
                "scope": {"resourceTypeId": room_type["id"]},
                "consequence": "require_payment",
            }
        ],
        0,
    )
    assert bad.status_code == 422
    assert [e["field"] for e in bad.json()["errors"]] == ["rules[0].consequence"]
