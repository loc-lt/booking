"""Worker: outbox delivery (once per subscriber, retries) and timers through transition()."""

from datetime import timedelta

import pytest
from django.utils import timezone

from kernel.models import ScheduledJob
from kernel.tenant_context import tenant_scope
from modules.booking.models import Booking
from modules.events import service as events
from modules.events.models import Outbox, ProcessedEvent
from tests.conftest import FLOW_APPROVAL, book, create_resource, create_type, local
from worker.management.commands.run_worker import run_due_jobs

pytestmark = pytest.mark.django_db


@pytest.fixture
def recorder(monkeypatch):
    """A subscriber that records what it saw; can be told to fail."""
    seen: list[str] = []
    state = {"fail": False}

    def handle(event):
        if state["fail"]:
            raise RuntimeError("mail server down")
        seen.append(event["name"])

    subs = [*events._subscribers, events.Subscriber("test_recorder", frozenset({"*"}), handle)]
    monkeypatch.setattr(events, "_subscribers", subs)
    return seen, state


def test_events_are_delivered_once(world, recorder):
    seen, _ = recorder
    create_type(world)
    assert events.relay_batch() >= 1
    assert "config.published" in seen
    event = Outbox.objects.get(event_type="config.published")
    assert event.published_at is not None
    # A redelivery (e.g. worker crashed before marking it) is skipped per subscriber.
    Outbox.objects.filter(id=event.id).update(published_at=None)
    events.relay_batch()
    assert seen.count("config.published") == 1
    assert ProcessedEvent.objects.filter(event_id=event.id, consumer="test_recorder").count() == 1


def test_failures_retry_later_without_blocking_other_subscribers(world, recorder):
    _, state = recorder
    state["fail"] = True
    create_type(world)
    events.relay_batch()
    event = Outbox.objects.get(event_type="config.published")
    assert event.published_at is None
    assert event.attempts == 1
    assert event.available_at > timezone.now()
    assert "mail server down" in event.last_error
    # The audit subscriber succeeded and is not run again.
    assert ProcessedEvent.objects.filter(event_id=event.id, consumer="audit_log").exists()
    state["fail"] = False
    Outbox.objects.filter(id=event.id).update(available_at=timezone.now())
    events.relay_batch()
    assert Outbox.objects.get(id=event.id).published_at is not None


def _due(booking_id, job_type):
    ScheduledJob.objects.filter(record_id=booking_id, job_type=job_type).update(
        run_at=timezone.now() - timedelta(seconds=1)
    )


def test_no_show_timer(world, day):
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    b = book(world, room["id"], local(day, 9), local(day, 10)).json()
    _due(b["id"], "MARK_NO_SHOW")
    assert run_due_jobs() == 1
    with tenant_scope(world.tenant_id):
        assert Booking.objects.get(id=b["id"]).status == "no_show"
    job = ScheduledJob.objects.get(record_id=b["id"], job_type="MARK_NO_SHOW")
    assert job.status == "DONE"
    detail = world.client("member").get(f"/api/v1/bookings/{b['id']}").json()
    assert detail["history"][-1]["actor"] == {"type": "system"}


def test_auto_complete_after_check_in(world, day, freeze):
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    b = book(world, room["id"], local(day, 9), local(day, 10)).json()
    freeze(local(day, 8, 55))
    world.client("member").post(f"/api/v1/bookings/{b['id']}/check-in")
    freeze(local(day, 10, 1))
    assert run_due_jobs() == 1
    with tenant_scope(world.tenant_id):
        assert Booking.objects.get(id=b["id"]).status == "completed"


def test_approval_timeout_rejects(world, day):
    rt = create_type(world, flowConfig=FLOW_APPROVAL)
    room = create_resource(world, rt["id"])
    b = book(world, room["id"], local(day, 9), local(day, 10)).json()
    _due(b["id"], "APPROVAL_TIMEOUT")
    run_due_jobs()
    with tenant_scope(world.tenant_id):
        assert Booking.objects.get(id=b["id"]).status == "rejected"


def test_a_moot_timer_does_nothing(world, day):
    rt = create_type(world)
    room = create_resource(world, rt["id"])
    b = book(world, room["id"], local(day, 9), local(day, 10)).json()
    world.client("member").post(f"/api/v1/bookings/{b['id']}/cancel")
    # Cancelling cancelled the timer; even if it ran, it would find nothing to do.
    assert ScheduledJob.objects.get(record_id=b["id"]).status == "CANCELLED"
    assert run_due_jobs() == 0
