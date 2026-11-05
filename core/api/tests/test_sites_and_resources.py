"""Sites, opening hours (site and per resource), exceptions, resource edits and maintenance
(API_KICH_BAN.md 4.1-4.3, 4.7, 4.8)."""

import pytest

from kernel.models import TransitionLog
from kernel.tenant_context import tenant_scope
from tests.conftest import book, create_resource, create_type, local

pytestmark = pytest.mark.django_db


def _slots(world, site_id, type_id, day, role="member"):
    response = world.client(role).get(
        "/api/v1/availability",
        {"siteId": str(site_id), "resourceTypeId": type_id, "date": day.isoformat()},
    )
    assert response.status_code == 200, response.json()
    return response.json()["slots"]


def test_create_site_with_hours_then_book_there(world, day):
    owner = world.client("owner")
    bad = owner.post("/api/v1/sites", {"name": "Hanoi", "timezone": "Mars/Base"}, format="json")
    assert bad.json()["errors"][0]["field"] == "timezone"
    site = owner.post(
        "/api/v1/sites",
        {"name": "Ha Noi Office", "timezone": "Asia/Ho_Chi_Minh", "address": {"city": "Ha Noi"}},
        format="json",
    )
    assert site.status_code == 201, site.json()
    s = site.json()
    assert (s["code"], s["status"], s["address"]) == ("ha-noi-office", "active", {"city": "Ha Noi"})
    assert (
        owner.post(
            "/api/v1/sites",
            {"name": "Ha Noi Office", "timezone": "Asia/Ho_Chi_Minh"},
            format="json",
        ).status_code
        == 422
    )  # same code

    rt = create_type(world)
    room = create_resource(world, rt["id"], site_id=s["id"])
    # No hours yet: closed every day.
    assert _slots(world, s["id"], rt["id"], day) == []
    hours = owner.put(
        f"/api/v1/sites/{s['id']}/hours",
        {"weekly": [{"weekday": d, "opens": "09:00", "closes": "11:00"} for d in range(7)]},
        format="json",
    )
    assert hours.status_code == 200, hours.json()
    assert hours.json()["weekly"][0] == {"weekday": 0, "opens": "09:00", "closes": "11:00"}
    slots = _slots(world, s["id"], rt["id"], day)
    assert [x["start"][11:16] for x in slots] == ["09:00", "09:30", "10:00", "10:30"]
    assert book(world, room["id"], local(day, 9), local(day, 10)).status_code == 201
    late = book(world, room["id"], local(day, 11), local(day, 12))
    assert late.json()["reasons"][0]["ruleId"] == "availability.hours"


def test_hours_validation(world):
    response = world.client("owner").put(
        f"/api/v1/sites/{world.site_id}/hours",
        {
            "weekly": [
                {"weekday": 0, "opens": "09:00", "closes": "12:00"},
                {"weekday": 0, "opens": "11:00", "closes": "13:00"},
                {"weekday": 1, "opens": "18:00", "closes": "08:00"},
            ]
        },
        format="json",
    )
    assert response.status_code == 422
    assert {e["message"] for e in response.json()["errors"]} == {
        "Ranges overlap.",
        "opens must be before closes.",
    }
    assert (
        world.client("member")
        .put(f"/api/v1/sites/{world.site_id}/hours", {"weekly": []}, format="json")
        .status_code
        == 403
    )


def test_resource_hours_replace_the_site_hours(world, day):
    rt = create_type(world)
    early = create_resource(world, rt["id"], label="Early room")
    create_resource(world, rt["id"], label="Normal room")
    owner = world.client("owner")
    url = f"/api/v1/resources/{early['id']}/hours"
    assert owner.get(url).json()["inheritsSiteHours"] is True
    own = owner.put(
        url,
        {"weekly": [{"weekday": d, "opens": "06:00", "closes": "09:00"} for d in range(7)]},
        format="json",
    )
    assert own.json()["inheritsSiteHours"] is False
    by_start = {
        x["start"][11:16]: x["resourceIds"] for x in _slots(world, world.site_id, rt["id"], day)
    }
    assert by_start["06:00"] == [early["id"]]
    assert early["id"] not in by_start["10:00"]
    assert owner.delete(url).json()["inheritsSiteHours"] is True


def test_block_exception_returns_affected_bookings_and_blocks_new_ones(world, day):
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    booked = book(world, room["id"], local(day, 14), local(day, 15)).json()
    staff = world.client("staff")
    response = staff.post(
        "/api/v1/availability-exceptions",
        {
            "resourceId": room["id"],
            "kind": "block",
            "start": local(day, 13).isoformat(),
            "end": local(day, 17).isoformat(),
            "reasonCode": "maintenance",
            "note": "Projector repair",
        },
        format="json",
    )
    # Staff have no availability.manage by default.
    assert response.status_code == 403
    response = world.client("admin").post(
        "/api/v1/availability-exceptions",
        {
            "resourceId": room["id"],
            "kind": "block",
            "start": local(day, 13).isoformat(),
            "end": local(day, 17).isoformat(),
            "reasonCode": "maintenance",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert [b["id"] for b in body["affectedBookings"]] == [booked["id"]]
    # The existing booking stays; new ones are refused.
    assert (
        world.client("member").get(f"/api/v1/bookings/{booked['id']}").json()["status"]
        == "confirmed"
    )
    denied = book(world, room["id"], local(day, 16), local(day, 17), role="member2")
    assert denied.json()["reasons"][0]["ruleId"] == "availability.hours"
    listed = world.client("admin").get(
        "/api/v1/availability-exceptions", {"resourceId": room["id"]}
    )
    assert [e["id"] for e in listed.json()["data"]] == [body["exception"]["id"]]
    gone = world.client("admin").delete(
        f"/api/v1/availability-exceptions/{body['exception']['id']}"
    )
    assert gone.status_code == 204
    assert (
        book(world, room["id"], local(day, 16), local(day, 17), role="member2").status_code == 201
    )


def test_site_holiday_and_extra_opening(world, day):
    rt = create_type(world)
    create_resource(world, rt["id"])
    admin = world.client("admin")
    admin.post(
        "/api/v1/availability-exceptions",
        {
            "siteId": str(world.site_id),
            "kind": "block",
            "start": local(day, 0).isoformat(),
            "end": local(day, 23, 59).isoformat(),
            "reasonCode": "holiday",
        },
        format="json",
    )
    assert _slots(world, world.site_id, rt["id"], day) == []
    admin.post(
        "/api/v1/availability-exceptions",
        {
            "siteId": str(world.other_site_id),
            "kind": "open",
            "start": local(day, 20).isoformat(),
            "end": local(day, 22).isoformat(),
        },
        format="json",
    )
    other_room = create_resource(world, rt["id"], label="Night room", site_id=world.other_site_id)
    starts = [x["start"][11:16] for x in _slots(world, world.other_site_id, rt["id"], day)]
    assert starts[-1] == "21:30"
    assert book(world, other_room["id"], local(day, 20), local(day, 21)).status_code == 201
    neither = admin.post(
        "/api/v1/availability-exceptions",
        {"kind": "block", "start": local(day, 1).isoformat(), "end": local(day, 2).isoformat()},
        format="json",
    )
    assert neither.status_code == 422


def test_edit_resource_values_are_checked_against_the_latest_form(world):
    rt = create_type(
        world,
        fields=[{"key": "seats", "label": "Seats", "type": "integer", "validation": {"max": 20}}],
    )
    room = create_resource(world, rt["id"], seats=4)
    owner = world.client("owner")
    url = f"/api/v1/resources/{room['id']}"
    bad = owner.patch(url, {"customFieldValues": {"seats": 50}}, format="json")
    assert bad.json()["errors"][0]["field"] == "customFieldValues.seats"
    ok = owner.patch(url, {"label": "Room Alpha", "customFieldValues": {"seats": 8}}, format="json")
    assert ok.status_code == 200
    assert (ok.json()["label"], ok.json()["customFieldValues"]) == ("Room Alpha", {"seats": 8})
    assert world.client("member").patch(url, {"label": "x"}, format="json").status_code == 403


def test_maintenance_hides_the_resource_and_lists_its_bookings(world, day):
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    booked = book(world, room["id"], local(day, 9), local(day, 10)).json()
    owner = world.client("owner")
    moved = owner.post(
        f"/api/v1/resources/{room['id']}/maintenance", {"reason": "Leak"}, format="json"
    )
    assert moved.status_code == 200, moved.json()
    assert moved.json()["resource"]["status"] == "maintenance"
    assert [b["id"] for b in moved.json()["affectedBookings"]] == [booked["id"]]
    assert all(
        room["id"] not in s["resourceIds"] for s in _slots(world, world.site_id, rt["id"], day)
    )
    denied = book(world, room["id"], local(day, 11), local(day, 12))
    assert denied.json()["reasons"][0]["ruleId"] == "resource.status"
    assert owner.post(f"/api/v1/resources/{room['id']}/maintenance").status_code == 409
    listed = owner.get("/api/v1/resources", {"status": "maintenance"}).json()["data"]
    assert [r["id"] for r in listed] == [room["id"]]
    back = owner.post(f"/api/v1/resources/{room['id']}/activate")
    assert back.json()["resource"]["status"] == "active"
    assert back.json()["affectedBookings"] == []
    with tenant_scope(world.tenant_id):
        moves = TransitionLog.objects.filter(object_code="resource", record_id=room["id"])
        assert [(m.from_status, m.to_status) for m in moves.order_by("at")] == [
            ("ACTIVE", "MAINTENANCE"),
            ("MAINTENANCE", "ACTIVE"),
        ]
