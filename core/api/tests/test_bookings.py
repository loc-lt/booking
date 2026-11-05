"""The booking pipeline and the lifecycle actions over HTTP (API_KICH_BAN.md 6.2-6.8)."""

from datetime import timedelta

import pytest

from kernel.models import ScheduledJob, TransitionLog
from kernel.tenant_context import tenant_scope
from modules.booking.models import BookingAllocation
from modules.events.models import Outbox
from modules.payments.models import Payment
from tests.conftest import FLOW_APPROVAL, FLOW_INSTANT, book, create_resource, create_type, local


@pytest.fixture
def room(world):
    rt = create_type(
        world,
        fields=[
            {
                "key": "attendee_count",
                "label": "Attendees",
                "type": "integer",
                "scope": "booking",
                "required": True,
                "validation": {"min": 1, "max": 10},
            }
        ],
    )
    return {"type": rt, **create_resource(world, rt["id"])}


@pytest.fixture
def approval_room(world):
    rt = create_type(world, key="board_room", flowConfig=FLOW_APPROVAL)
    return {"type": rt, **create_resource(world, rt["id"], label="Board room")}


def test_instant_booking_is_confirmed_with_history_and_applied_config(world, room, day):
    response = book(
        world, room["id"], local(day, 9), local(day, 10), customFieldValues={"attendee_count": 3}
    )
    assert response.status_code == 201, response.json()
    b = response.json()
    assert b["status"] == "confirmed"
    assert b["start"] == local(day, 9).isoformat()  # in the site's offset
    assert b["memberId"] == str(world.membership_id("member"))
    applied = b["appliedConfig"]
    assert {k: applied[k] for k in ("flowConfigVersion", "ruleSetVersion", *FLOW_INSTANT)} == {
        "flowConfigVersion": 1,
        "ruleSetVersion": 0,
        **FLOW_INSTANT,
    }
    assert applied["payment"]["mode"] == "none"
    assert b["history"] == [
        {
            "toStatus": "confirmed",
            "occurredAt": b["history"][0]["occurredAt"],
            "actor": {"type": "user", "id": b["memberId"]},
        }
    ]
    with tenant_scope(world.tenant_id):
        allocation = BookingAllocation.objects.get(booking_id=b["id"])
        assert allocation.effect == "LOCK"
        assert Payment.objects.get(booking_id=b["id"]).status == "WAIVED"
        jobs = set(
            ScheduledJob.objects.filter(record_id=b["id"]).values_list("job_type", flat=True)
        )
        assert jobs == {"MARK_NO_SHOW"}  # check-in required
    assert list(
        Outbox.objects.filter(aggregate_id=b["id"]).values_list("event_type", flat=True)
    ) == ["booking.confirmed"]


def test_booking_fields_are_validated(world, room, day):
    response = book(
        world, room["id"], local(day, 9), local(day, 10), customFieldValues={"attendee_count": 99}
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "customFieldValues.attendee_count"
    missing = book(world, room["id"], local(day, 11), local(day, 12))
    assert missing.json()["errors"] == [
        {"field": "customFieldValues.attendee_count", "message": "This field is required."}
    ]


@pytest.mark.parametrize(
    ("start", "end", "field"),
    [((9, 0), (9, 0), "end"), ((9, 10), (10, 0), "start"), ((9, 0), (9, 45), "end")],
    ids=["empty", "off-slot-start", "off-slot-length"],
)
def test_bad_times_fail_validation(world, room, day, start, end, field):
    response = book(
        world,
        room["id"],
        local(day, *start),
        local(day, *end),
        customFieldValues={"attendee_count": 1},
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == field


def test_times_without_offset_are_refused(world, room, day):
    response = world.client("member").post(
        "/api/v1/bookings",
        {"resourceId": room["id"], "start": f"{day}T09:00:00", "end": f"{day}T10:00:00"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="no-offset",
    )
    assert response.status_code == 422
    assert {e["field"] for e in response.json()["errors"]} == {"start", "end"}


def test_closed_hours_and_policy_limits_are_denied_with_reasons(world, room, day):
    closed = book(
        world, room["id"], local(day, 21), local(day, 22), customFieldValues={"attendee_count": 1}
    )
    assert closed.status_code == 422
    assert closed.json()["code"] == "BOOKING_DENIED"
    assert closed.json()["reasons"][0]["ruleId"] == "availability.hours"

    too_long = book(
        world, room["id"], local(day, 8), local(day, 17), customFieldValues={"attendee_count": 1}
    )
    assert too_long.json()["reasons"] == [
        {"ruleId": "policy.max_duration_seconds", "message": "At most 480 minutes."}
    ]

    far = local(day + timedelta(days=120), 9)
    too_far = book(
        world, room["id"], far, far + timedelta(hours=1), customFieldValues={"attendee_count": 1}
    )
    assert too_far.json()["reasons"][0]["ruleId"] == "policy.booking_window_days"


def test_idempotency_key_replays_the_first_result(world, room, day):
    args = (world, room["id"], local(day, 9), local(day, 10))
    first = book(*args, key="same", customFieldValues={"attendee_count": 2})
    again = book(*args, key="same", customFieldValues={"attendee_count": 2})
    assert first.status_code == again.status_code == 201
    assert again.json()["id"] == first.json()["id"]
    assert again["Idempotent-Replayed"] == "true"

    other_body = book(
        world,
        room["id"],
        local(day, 11),
        local(day, 12),
        key="same",
        customFieldValues={"attendee_count": 2},
    )
    assert other_body.status_code == 422
    assert other_body.json()["errors"][0]["field"] == "Idempotency-Key"


def test_idempotency_key_is_required(world, room, day):
    response = world.client("member").post(
        "/api/v1/bookings",
        {
            "resourceId": room["id"],
            "start": local(day, 9).isoformat(),
            "end": local(day, 10).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "Idempotency-Key"


def test_overlap_is_slot_taken_and_saves_nothing(world, room, day):
    ok = book(
        world, room["id"], local(day, 9), local(day, 10), customFieldValues={"attendee_count": 1}
    )
    assert ok.status_code == 201
    clash = book(
        world,
        room["id"],
        local(day, 9, 30),
        local(day, 10, 30),
        role="member2",
        customFieldValues={"attendee_count": 1},
    )
    assert clash.status_code == 409
    assert clash.json()["code"] == "SLOT_TAKEN"
    adjacent = book(
        world,
        room["id"],
        local(day, 10),
        local(day, 11),
        role="member2",
        customFieldValues={"attendee_count": 1},
    )
    assert adjacent.status_code == 201  # [start, end): touching is not overlapping


def test_approval_flow(world, approval_room, day):
    b = book(world, approval_room["id"], local(day, 9), local(day, 10)).json()
    assert b["status"] == "pending_approval"
    with tenant_scope(world.tenant_id):
        assert BookingAllocation.objects.get(booking_id=b["id"]).effect == "HOLD"

    # A member can't approve; staff of the booking's site can.
    assert world.client("member").post(f"/api/v1/bookings/{b['id']}/approve").status_code == 403
    approved = world.client("staff").post(f"/api/v1/bookings/{b['id']}/approve")
    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == "confirmed"
    assert [(h.get("fromStatus"), h["toStatus"]) for h in body["history"]] == [
        (None, "pending_approval"),
        ("pending_approval", "confirmed"),
    ]
    # Approving twice is a move the lifecycle doesn't allow.
    again = world.client("staff").post(f"/api/v1/bookings/{b['id']}/approve")
    assert again.status_code == 409
    assert again.json()["code"] == "INVALID_TRANSITION"


def test_reject_needs_a_reason_and_frees_the_slot(world, approval_room, day):
    b = book(world, approval_room["id"], local(day, 9), local(day, 10)).json()
    url = f"/api/v1/bookings/{b['id']}/reject"
    assert world.client("staff").post(url, {"reason": ""}, format="json").status_code == 422
    rejected = world.client("staff").post(url, {"reason": "Room is reserved"}, format="json")
    assert rejected.json()["status"] == "rejected"
    retry = book(world, approval_room["id"], local(day, 9), local(day, 10), role="member2")
    assert retry.status_code == 201


def test_staff_of_another_site_cannot_act(world, day):
    rt = create_type(world, key="desk", flowConfig=FLOW_APPROVAL)
    desk = create_resource(world, rt["id"], label="Desk 1", site_id=world.other_site_id)
    b = book(world, desk["id"], local(day, 9), local(day, 10)).json()
    # staff is limited to the first site: the booking is not even visible to them.
    assert world.client("staff").post(f"/api/v1/bookings/{b['id']}/approve").status_code == 404
    assert world.client("admin").post(f"/api/v1/bookings/{b['id']}/approve").status_code == 200


def test_check_in_only_inside_the_window(world, room, day, freeze):
    b = book(
        world, room["id"], local(day, 9), local(day, 10), customFieldValues={"attendee_count": 1}
    ).json()
    url = f"/api/v1/bookings/{b['id']}/check-in"
    freeze(local(day, 8, 30))  # opens 15 minutes before
    early = world.client("member").post(url)
    assert early.status_code == 409
    assert early.json()["code"] == "INVALID_TRANSITION"
    freeze(local(day, 8, 50))
    assert world.client("member2").post(url).status_code == 404  # not their booking
    ok = world.client("member").post(url)
    assert ok.status_code == 200
    assert ok.json()["status"] == "checked_in"
    with tenant_scope(world.tenant_id):
        jobs = dict(
            ScheduledJob.objects.filter(record_id=b["id"]).values_list("job_type", "status")
        )
    assert jobs == {"MARK_NO_SHOW": "CANCELLED", "AUTO_COMPLETE": "PENDING"}


def test_cancel_deadline_applies_to_members_not_staff(world, room, day, freeze):
    b1 = book(
        world, room["id"], local(day, 9), local(day, 10), customFieldValues={"attendee_count": 1}
    ).json()
    b2 = book(
        world, room["id"], local(day, 11), local(day, 12), customFieldValues={"attendee_count": 1}
    ).json()
    freeze(local(day, 8, 30))  # 30 min before b1: past the 60-minute deadline
    late = world.client("member").post(f"/api/v1/bookings/{b1['id']}/cancel")
    assert late.status_code == 409
    assert (
        world.client("member").post(f"/api/v1/bookings/{b2['id']}/cancel").json()["status"]
        == "cancelled"
    )
    by_staff = world.client("staff").post(f"/api/v1/bookings/{b1['id']}/cancel")
    assert by_staff.json()["status"] == "cancelled"
    with tenant_scope(world.tenant_id):
        assert not BookingAllocation.objects.filter(
            booking_id__in=[b1["id"], b2["id"]], closed_at__isnull=True
        ).exists()


def test_old_bookings_keep_the_policy_they_were_made_under(world, room, day):
    b = book(
        world, room["id"], local(day, 9), local(day, 10), customFieldValues={"attendee_count": 1}
    ).json()
    world.client("owner").patch(
        f"/api/v1/resource-types/{room['type']['id']}",
        {"baseVersion": 1, "flowConfig": FLOW_APPROVAL},
        format="json",
    )
    old = world.client("member").get(f"/api/v1/bookings/{b['id']}").json()
    assert old["appliedConfig"]["flowConfigVersion"] == 1
    assert old["appliedConfig"]["confirmation"] == "instant"
    new = book(
        world, room["id"], local(day, 11), local(day, 12), customFieldValues={"attendee_count": 1}
    ).json()
    assert new["status"] == "pending_approval"
    assert new["appliedConfig"]["flowConfigVersion"] == 2


def test_list_visibility_and_filters(world, room, day):
    mine = book(
        world, room["id"], local(day, 9), local(day, 10), customFieldValues={"attendee_count": 1}
    ).json()
    theirs = book(
        world,
        room["id"],
        local(day, 11),
        local(day, 12),
        role="member2",
        customFieldValues={"attendee_count": 1},
    ).json()
    member_list = world.client("member").get("/api/v1/bookings").json()
    assert [x["id"] for x in member_list["data"]] == [mine["id"]]
    staff_list = world.client("staff").get("/api/v1/bookings").json()
    assert {x["id"] for x in staff_list["data"]} == {mine["id"], theirs["id"]}
    filtered = (
        world.client("staff")
        .get(
            "/api/v1/bookings",
            {"from": local(day, 10, 30).isoformat(), "to": local(day, 13).isoformat()},
        )
        .json()
    )
    assert [x["id"] for x in filtered["data"]] == [theirs["id"]]
    by_status = world.client("staff").get("/api/v1/bookings", {"status": "cancelled"}).json()
    assert by_status["data"] == []
    bad = world.client("staff").get("/api/v1/bookings", {"status": "PENDING"})
    assert bad.status_code == 422


def test_staff_can_book_for_a_member(world, room, day):
    member_id = str(world.membership_id("member"))
    response = book(
        world,
        room["id"],
        local(day, 9),
        local(day, 10),
        role="staff",
        memberId=member_id,
        customFieldValues={"attendee_count": 1},
    )
    assert response.status_code == 201
    assert response.json()["memberId"] == member_id
    not_allowed = book(
        world,
        room["id"],
        local(day, 11),
        local(day, 12),
        role="member2",
        memberId=member_id,
        customFieldValues={"attendee_count": 1},
    )
    assert not_allowed.status_code == 403


def test_every_move_writes_one_history_row_and_one_event(world, approval_room, day):
    b = book(world, approval_room["id"], local(day, 9), local(day, 10)).json()
    world.client("staff").post(f"/api/v1/bookings/{b['id']}/approve")
    world.client("member").post(f"/api/v1/bookings/{b['id']}/cancel")
    with tenant_scope(world.tenant_id):
        logs = list(
            TransitionLog.objects.filter(record_id=b["id"])
            .order_by("at")
            .values_list("action", "to_status")
        )
    assert logs == [
        ("REQUIRE_APPROVAL", "pending_approval"),
        ("APPROVE", "confirmed"),
        ("CANCEL", "cancelled"),
    ]
    events = list(
        Outbox.objects.filter(aggregate_id=b["id"])
        .order_by("occurred_at")
        .values_list("event_type", flat=True)
    )
    assert events == ["booking.approval_requested", "booking.confirmed", "booking.cancelled"]


pytestmark = pytest.mark.django_db
