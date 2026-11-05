"""Free/busy search (API_KICH_BAN.md 6.1) and the availability engine."""

from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from kernel.tenant_context import tenant_scope
from modules.availability import service as availability
from modules.config.models import PolicyVersion
from tests.conftest import TZ, book, create_resource, create_type, local


def _search(world, rt_id, day, **extra):
    params = {"siteId": str(world.site_id), "resourceTypeId": rt_id, "date": day.isoformat()}
    params.update(extra)
    response = world.client("member").get("/api/v1/availability", params)
    assert response.status_code == 200, response.json()
    return response.json()


@pytest.mark.django_db
def test_slots_follow_site_hours_in_local_time(world, day):
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    body = _search(world, rt["id"], day)
    assert body["slotMinutes"] == 30
    slots = body["slots"]
    assert len(slots) == 24  # 08:00-20:00 in 30-minute slots
    assert slots[0]["start"] == local(day, 8).isoformat()  # "...T08:00:00+07:00"
    assert slots[-1]["end"] == local(day, 20).isoformat()
    assert all(s["resourceIds"] == [room["id"]] for s in slots)


@pytest.mark.django_db
def test_a_booking_makes_its_slots_busy(world, day):
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    assert book(world, room["id"], local(day, 9), local(day, 10)).status_code == 201
    slots = {s["start"]: s["resourceIds"] for s in _search(world, rt["id"], day)["slots"]}
    assert slots[local(day, 9).isoformat()] == []
    assert slots[local(day, 9, 30).isoformat()] == []
    assert slots[local(day, 10).isoformat()] == [room["id"]]


@pytest.mark.django_db
def test_buffers_widen_busy_time(world, day):
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    with tenant_scope(world.tenant_id):
        pv = PolicyVersion.objects.get(resource_type_id=rt["id"])
        PolicyVersion.objects.filter(id=pv.id).update(body={**pv.body, "buffer_after_seconds": 900})
    book(world, room["id"], local(day, 9), local(day, 10))
    slots = {s["start"]: s["resourceIds"] for s in _search(world, rt["id"], day)["slots"]}
    # 10:00 would start inside the 15-minute cleaning buffer.
    assert slots[local(day, 10).isoformat()] == []
    assert slots[local(day, 10, 30).isoformat()] == [room["id"]]
    # Booking 10:00 is refused by the database guard.
    response = book(world, room["id"], local(day, 10), local(day, 10, 30), role="member2")
    assert response.status_code == 409
    assert response.json()["code"] == "SLOT_TAKEN"


@pytest.mark.django_db
def test_blackouts_remove_slots(world, day):
    rt = create_type(world)
    create_resource(world, rt["id"])
    with tenant_scope(world.tenant_id):
        availability.add_exception(
            tenant_id=world.tenant_id,
            location_id=world.site_id,
            kind="BLOCK",
            start=local(day, 12),
            end=local(day, 14),
            reason_code="maintenance",
        )
    starts = [s["start"] for s in _search(world, rt["id"], day)["slots"]]
    assert local(day, 12).isoformat() not in starts
    assert local(day, 13, 30).isoformat() not in starts
    assert local(day, 14).isoformat() in starts
    assert len(starts) == 20


@pytest.mark.django_db
def test_unknown_resource_filter_is_a_validation_error(world, day):
    rt = create_type(world)
    response = world.client("member").get(
        "/api/v1/availability",
        {
            "siteId": str(world.site_id),
            "resourceTypeId": rt["id"],
            "date": day.isoformat(),
            "resourceId": rt["id"],
        },
    )
    assert response.status_code == 422


# ---------- engine, no HTTP ----------


@pytest.mark.django_db
def test_daylight_saving_day_is_cut_in_local_time(world):
    """Europe/Berlin, 2026-03-29: clocks jump from 02:00 to 03:00. A site open 00:00-06:00
    is open 5 real hours that day, and slots never start inside the missing hour."""
    berlin = "Europe/Berlin"
    with tenant_scope(world.tenant_id):
        from modules.resources import service as resources

        site = resources.create_location(
            tenant_id=world.tenant_id, code="berlin", name="Berlin", timezone_name=berlin
        )
        availability.set_weekly_hours(
            tenant_id=world.tenant_id,
            location_id=site.id,
            hours={d: [(time(0), time(6))] for d in range(7)},
        )
        ref = availability.ResourceRef(id=site.id, location_id=site.id)
        dst = date(2026, 3, 29)
        start, end = availability.day_bounds(dst, berlin)
        opened = availability.open_intervals(
            resources=[ref], timezone_name=berlin, start=start, end=end
        )[site.id]
        assert sum((e - s for s, e in opened), timedelta()) == timedelta(hours=5)
        slots = availability.free_slots(
            resources=[ref],
            timezone_name=berlin,
            day=dst,
            slot_minutes=60,
            busy={},
            buffer_before=timedelta(),
            buffer_after=timedelta(),
        )
        local_hours = [s.astimezone(ZoneInfo(berlin)).hour for s, _, _ in slots]
        assert local_hours == [0, 1, 3, 4, 5]


def test_midnight_belongs_to_the_site_day():
    start, end = availability.day_bounds(date(2026, 12, 15), TZ)
    assert start.isoformat() == "2026-12-14T17:00:00+00:00"  # local midnight, +07:00
    assert (end - start) == timedelta(days=1)
