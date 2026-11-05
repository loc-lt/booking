"""The lifecycle table, exhaustively: every allowed move works, every other move raises
INVALID_TRANSITION, and each move writes one history row and one event."""

from datetime import timedelta

import pytest
from django.utils import timezone

from kernel.errors import InvalidTransition
from kernel.models import TransitionLog
from kernel.tenant_context import tenant_scope
from modules.booking.lifecycle import MOVES, SUBMITTED, Actor, Applied, transition
from modules.booking.models import Booking, BookingStatus
from modules.config.policy import DEFAULT_BODY
from modules.events.models import Outbox
from tests.conftest import create_resource, create_type

ALL_MOVES = sorted({move for _, move in MOVES})
STATUSES = [SUBMITTED, *BookingStatus.values]
# A body with no time guards, so only the table decides.
OPEN_BODY = {
    **DEFAULT_BODY,
    "checkin_open_before_seconds": 10**7,
    "cancel_allowed_until_seconds": 0,
}


@pytest.fixture
def make_booking(world):
    rt = create_type(world)
    res = create_resource(world, rt["id"])

    def make(status: str | None) -> Booking:
        from modules.config.models import PolicyVersion
        from modules.users.models import Membership

        start = timezone.now() + timedelta(hours=1)
        booking = Booking(
            tenant_id=world.tenant_id,
            public_code=f"T-{Booking.objects.count()}",
            location_id=world.site_id,
            resource_id=res["id"],
            resource_type_id=rt["id"],
            booking_mode="EXCLUSIVE",
            booker_membership_id=Membership.objects.first().id,
            status=status,
            start_at=start,
            end_at=start + timedelta(hours=1),
            local_date=start.date(),
            policy_version_id=PolicyVersion.objects.get(resource_type_id=rt["id"]).id,
            currency="VND",
        )
        if status is not None:
            booking.save()
        return booking

    return make


def _targets(status: str, move: str) -> list[str]:
    return sorted(MOVES.get((status, move), ()))


@pytest.mark.django_db
@pytest.mark.parametrize("status", STATUSES)
@pytest.mark.parametrize("move", ALL_MOVES)
def test_lifecycle_table(world, make_booking, status, move):
    applied = Applied(version=1, body=OPEN_BODY)
    with tenant_scope(world.tenant_id):
        booking = make_booking(None if status == SUBMITTED else status)
        targets = _targets(status, move)
        if not targets:
            with pytest.raises(InvalidTransition):
                transition(booking, move, actor=Actor.system(), applied=applied)
            return
        for to in targets:
            if status != SUBMITTED:
                Booking.objects.filter(id=booking.id).update(status=status)
                booking.refresh_from_db()
            before_logs = TransitionLog.objects.filter(record_id=booking.id).count()
            before_events = Outbox.objects.filter(aggregate_id=booking.id).count()
            transition(booking, move, actor=Actor.system(), applied=applied, to=to)
            assert Booking.objects.get(id=booking.id).status == to
            assert TransitionLog.objects.filter(record_id=booking.id).count() == before_logs + 1
            assert Outbox.objects.filter(aggregate_id=booking.id).count() == before_events + 1


def test_every_documented_move_is_in_the_table():
    """The table in docs/domain/booking.md, written out again by hand."""
    documented = {
        ("submitted", "require_payment", "awaiting_payment"),
        ("submitted", "require_approval", "pending_approval"),
        ("awaiting_payment", "paid", "pending_approval"),
        ("submitted", "confirm", "confirmed"),
        ("awaiting_payment", "paid", "confirmed"),
        ("pending_approval", "approve", "confirmed"),
        ("awaiting_payment", "payment_failed", "expired"),
        ("awaiting_payment", "expire", "expired"),
        ("pending_approval", "reject", "rejected"),
        ("awaiting_payment", "cancel", "cancelled"),
        ("pending_approval", "cancel", "cancelled"),
        ("confirmed", "cancel", "cancelled"),
        ("confirmed", "check_in", "checked_in"),
        ("confirmed", "no_show", "no_show"),
        ("checked_in", "complete", "completed"),
        # README open decision 4, not in the docs table yet: timer only, when the policy
        # needs no check-in (guarded in lifecycle._guard).
        ("confirmed", "complete", "completed"),
    }
    table = {(f, m, t) for (f, m), targets in MOVES.items() for t in targets}
    assert table == documented
