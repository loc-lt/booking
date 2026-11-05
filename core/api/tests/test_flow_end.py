"""How bookings end: check-out, auto-complete without check-in; and the event log."""

from datetime import timedelta

import pytest
from django.utils import timezone

from kernel.models import ScheduledJob
from tests.conftest import FLOW_INSTANT, book, create_resource, create_type, local
from worker.management.commands.run_worker import run_due_jobs

pytestmark = pytest.mark.django_db

NO_CHECK_IN = {
    **FLOW_INSTANT,
    "checkIn": {"required": False, "opensMinutesBefore": 15, "noShowAfterMinutes": 15},
}


def test_check_out_frees_the_rest_of_the_slot(world, freeze, day):
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    b = book(world, room["id"], local(day, 9), local(day, 11)).json()
    freeze(local(day, 9, 5))
    assert world.client("member").post(f"/api/v1/bookings/{b['id']}/check-out").status_code == 409
    world.client("member").post(f"/api/v1/bookings/{b['id']}/check-in")
    assert world.client("member2").post(f"/api/v1/bookings/{b['id']}/check-out").status_code == 404
    out = world.client("member").post(f"/api/v1/bookings/{b['id']}/check-out")
    assert out.status_code == 200, out.json()
    assert [h["toStatus"] for h in out.json()["history"]] == [
        "confirmed",
        "checked_in",
        "completed",
    ]
    assert (
        book(world, room["id"], local(day, 10), local(day, 11), role="member2").status_code == 201
    )
    assert not ScheduledJob.objects.filter(record_id=b["id"], status="PENDING").exists()


def test_confirmed_without_check_in_completes_at_the_end(world, day):
    rt = create_type(world, key="desk", flowConfig=NO_CHECK_IN)
    desk = create_resource(world, rt["id"])
    b = book(world, desk["id"], local(day, 9), local(day, 10)).json()
    jobs = ScheduledJob.objects.filter(record_id=b["id"], status="PENDING")
    assert [j.job_type for j in jobs] == ["AUTO_COMPLETE"]
    # Nobody but the timer completes a confirmed booking.
    assert world.client("staff").post(f"/api/v1/bookings/{b['id']}/check-out").status_code == 409
    jobs.update(run_at=timezone.now() - timedelta(seconds=1))
    run_due_jobs()
    after = world.client("member").get(f"/api/v1/bookings/{b['id']}").json()
    assert after["status"] == "completed"
    assert after["history"][-1]["actor"] == {"type": "system"}


def test_event_log_is_tenant_private(world, world_b, day):
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    b = book(world, room["id"], local(day, 9), local(day, 10)).json()
    log = world.client("owner").get("/api/v1/events", {"subjectId": b["id"]}).json()["data"]
    assert [e["name"] for e in log] == ["booking.confirmed"]
    assert log[0]["delivery"]["publishedAt"] is None
    names = {
        e["name"]
        for e in world.client("owner").get("/api/v1/events", {"limit": 100}).json()["data"]
    }
    assert {"config.published", "resource.created", "booking.confirmed"} <= names
    assert world_b.client("owner").get("/api/v1/events").json()["data"] == []
    assert world.client("member").get("/api/v1/events").status_code == 403
    filtered = world.client("owner").get("/api/v1/events", {"name": "booking."}).json()["data"]
    assert {e["name"] for e in filtered} == {"booking.confirmed"}
