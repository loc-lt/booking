"""Configuration flexibility without code changes: fields added or archived later, policy
limits/buffers/slot size, version history and rollback (docs/domain/configuration.md)."""

import pytest

from kernel.tenant_context import tenant_scope
from modules.booking.models import Booking
from modules.events.models import Outbox
from modules.resources.models import Resource
from tests.conftest import FLOW_APPROVAL, FLOW_INSTANT, book, create_resource, create_type, local

pytestmark = pytest.mark.django_db


def test_add_a_field_later_without_touching_old_records(world, day):
    rt = create_type(world)
    old_room = create_resource(world, rt["id"], label="Old room")
    owner = world.client("owner")
    url = f"/api/v1/resource-types/{rt['id']}/fields"
    added = owner.post(
        url,
        {
            "fields": [
                {"key": "has_tv", "label": "Has TV", "type": "boolean", "required": True},
                {
                    "key": "purpose",
                    "label": "Purpose",
                    "type": "select",
                    "scope": "booking",
                    "options": [{"value": "meeting", "label": "Meeting"}],
                },
            ]
        },
        format="json",
    )
    assert added.status_code == 200, added.json()
    assert [f["key"] for f in added.json()["fields"]] == ["has_tv", "purpose"]
    assert (
        owner.post(
            url, {"fields": [{"key": "has_tv", "label": "Again", "type": "boolean"}]}, format="json"
        ).status_code
        == 422
    )
    # New resources must fill the new required field; the old one keeps its old form.
    missing = owner.post(
        "/api/v1/resources",
        {"resourceTypeId": rt["id"], "siteId": str(world.site_id), "label": "New room"},
        format="json",
    )
    assert missing.json()["errors"][0]["field"] == "customFieldValues.has_tv"
    create_resource(world, rt["id"], label="New room", has_tv=True)
    with tenant_scope(world.tenant_id):
        old_schema = Resource.objects.get(id=old_room["id"]).schema_id
    assert old_schema is not None
    # Bookings now accept (and check) the booking-scoped field.
    bad = book(
        world, old_room["id"], local(day, 9), local(day, 10), customFieldValues={"purpose": "party"}
    )
    assert bad.json()["errors"][0]["field"] == "customFieldValues.purpose"
    ok = book(
        world,
        old_room["id"],
        local(day, 9),
        local(day, 10),
        customFieldValues={"purpose": "meeting"},
    )
    assert ok.status_code == 201


def test_archive_a_field(world):
    rt = create_type(
        world, fields=[{"key": "floor", "label": "Floor", "type": "integer", "required": True}]
    )
    owner = world.client("owner")
    archived = owner.post(f"/api/v1/resource-types/{rt['id']}/fields/floor/archive")
    assert archived.json()["fields"] == []
    create_resource(world, rt["id"], label="No floor needed")
    assert owner.post(f"/api/v1/resource-types/{rt['id']}/fields/floor/archive").status_code == 404
    # Keys are permanent: an archived key cannot come back as a different field.
    again = owner.post(
        f"/api/v1/resource-types/{rt['id']}/fields",
        {"fields": [{"key": "floor", "label": "Floor", "type": "text"}]},
        format="json",
    )
    assert again.status_code == 422


def test_limits_buffers_and_slot_size_are_settings(world, day):
    flow = {
        **FLOW_INSTANT,
        "limits": {"minDurationMinutes": 60, "maxDurationMinutes": 120, "bookingWindowDays": 30},
        "buffers": {"afterMinutes": 30},
    }
    rt = create_type(world, key="studio", flowConfig=flow)
    assert rt["flowConfig"]["limits"]["maxDurationMinutes"] == 120
    room = create_resource(world, rt["id"])
    short = book(world, room["id"], local(day, 9), local(day, 9, 30))
    assert short.json()["reasons"][0]["ruleId"] == "policy.min_duration_seconds"
    long = book(world, room["id"], local(day, 9), local(day, 12))
    assert long.json()["reasons"][0]["ruleId"] == "policy.max_duration_seconds"
    assert book(world, room["id"], local(day, 9), local(day, 10)).status_code == 201
    # The 30-minute cleaning buffer blocks 10:00-10:30 for the next booking.
    assert (
        book(world, room["id"], local(day, 10), local(day, 11), role="member2").status_code == 409
    )
    assert (
        book(world, room["id"], local(day, 10, 30), local(day, 11, 30), role="member2").status_code
        == 201
    )

    owner = world.client("owner")
    patched = owner.patch(
        f"/api/v1/resource-types/{rt['id']}",
        {"baseVersion": 1, "slotMinutes": 60, "flowConfig": flow},
        format="json",
    )
    assert (patched.json()["slotMinutes"], patched.json()["version"]) == (60, 1)  # same policy
    slots = owner.get(
        "/api/v1/availability",
        {"siteId": str(world.site_id), "resourceTypeId": rt["id"], "date": day.isoformat()},
    ).json()
    assert slots["slotMinutes"] == 60
    bad = owner.patch(
        f"/api/v1/resource-types/{rt['id']}",
        {"baseVersion": 1, "slotMinutes": 7, "flowConfig": flow},
        format="json",
    )
    assert bad.json()["errors"][0]["field"] == "slotMinutes"
    crossed = owner.patch(
        f"/api/v1/resource-types/{rt['id']}",
        {"baseVersion": 1, "flowConfig": {**flow, "limits": {"minDurationMinutes": 300}}},
        format="json",
    )
    assert crossed.json()["errors"][0]["field"] == "flowConfig.limits.minDurationMinutes"


def test_version_history_and_restore(world, day):
    rt = create_type(world)
    owner = world.client("owner")
    url = f"/api/v1/resource-types/{rt['id']}"
    owner.patch(url, {"baseVersion": 1, "flowConfig": FLOW_APPROVAL}, format="json")
    versions = owner.get(f"{url}/versions").json()["data"]
    assert [(v["version"], v["status"]) for v in versions] == [(2, "published"), (1, "superseded")]
    assert versions[0]["flowConfig"]["confirmation"] == "approval"

    stale = owner.post(f"{url}/versions/1/restore", {"baseVersion": 1}, format="json")
    assert stale.status_code == 409
    restored = owner.post(f"{url}/versions/1/restore", {"baseVersion": 2}, format="json")
    assert restored.status_code == 200, restored.json()
    assert (restored.json()["version"], restored.json()["flowConfig"]["confirmation"]) == (
        3,
        "instant",
    )
    assert (
        world.client("staff")
        .post(f"{url}/versions/2/restore", {"baseVersion": 3}, format="json")
        .status_code
        == 403
    )
    room = create_resource(world, rt["id"])
    booked = book(world, room["id"], local(day, 9), local(day, 10)).json()
    assert booked["appliedConfig"]["flowConfigVersion"] == 3
    with tenant_scope(world.tenant_id):
        event = Outbox.objects.filter(event_type="config.published").order_by("-id").first()
        assert event.payload["changes"]["restoredFrom"] == 1
        assert Booking.objects.get(id=booked["id"]).policy_version.version == 3


def test_an_edit_that_changes_nothing_publishes_nothing(world):
    rt = create_type(world)
    response = world.client("owner").patch(
        f"/api/v1/resource-types/{rt['id']}",
        {"baseVersion": 1, "label": "Big room", "flowConfig": FLOW_INSTANT},
        format="json",
    )
    assert (response.json()["version"], response.json()["label"]) == (1, "Big room")
