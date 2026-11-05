"""The booking lifecycle (docs/domain/booking.md, "Allowed moves").

transition() is the ONLY code that changes bookings.status. Every move:
  1. is looked up in MOVES; anything else raises INVALID_TRANSITION,
  2. runs the guards of the move (check-in window, cancellation deadline),
  3. updates the status and its timestamp,
  4. runs the effects of the new status (allocation HOLD/LOCK/close, timers),
  5. writes one transition_log row and emits exactly one event,
all inside the caller's transaction.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from kernel.errors import InvalidTransition
from kernel.jobs import cancel_jobs, schedule_job
from kernel.models import ActorKind, TransitionLog
from kernel.request_context import current_request_id
from modules.booking.models import AllocationEffect, Booking, BookingAllocation
from modules.booking.models import BookingStatus as S
from modules.events import service as events

SUBMITTED = "submitted"  # entry point, never stored

# (from, move) -> allowed targets. Copied from the table in docs/domain/booking.md.
MOVES: dict[tuple[str, str], frozenset[str]] = {
    (SUBMITTED, "require_payment"): frozenset({S.AWAITING_PAYMENT}),
    (SUBMITTED, "require_approval"): frozenset({S.PENDING_APPROVAL}),
    (SUBMITTED, "confirm"): frozenset({S.CONFIRMED}),
    (S.AWAITING_PAYMENT, "paid"): frozenset({S.PENDING_APPROVAL, S.CONFIRMED}),
    (S.PENDING_APPROVAL, "approve"): frozenset({S.CONFIRMED}),
    (S.AWAITING_PAYMENT, "payment_failed"): frozenset({S.EXPIRED}),
    (S.AWAITING_PAYMENT, "expire"): frozenset({S.EXPIRED}),
    (S.PENDING_APPROVAL, "reject"): frozenset({S.REJECTED}),
    (S.AWAITING_PAYMENT, "cancel"): frozenset({S.CANCELLED}),
    (S.PENDING_APPROVAL, "cancel"): frozenset({S.CANCELLED}),
    (S.CONFIRMED, "cancel"): frozenset({S.CANCELLED}),
    (S.CONFIRMED, "check_in"): frozenset({S.CHECKED_IN}),
    (S.CONFIRMED, "no_show"): frozenset({S.NO_SHOW}),
    (S.CHECKED_IN, "complete"): frozenset({S.COMPLETED}),
    # Not in docs/domain/booking.md yet (README, open decision 4): a confirmed booking whose
    # policy needs no check-in completes at its end. Guarded below: timer only.
    (S.CONFIRMED, "complete"): frozenset({S.COMPLETED}),
}

EVENT_NAMES = {
    S.AWAITING_PAYMENT: "booking.awaiting_payment",
    S.PENDING_APPROVAL: "booking.approval_requested",
    S.CONFIRMED: "booking.confirmed",
    S.CHECKED_IN: "booking.checked_in",
    S.COMPLETED: "booking.completed",
    S.EXPIRED: "booking.expired",
    S.REJECTED: "booking.rejected",
    S.CANCELLED: "booking.cancelled",
    S.NO_SHOW: "booking.no_show",
}

TERMINAL = frozenset({S.COMPLETED, S.EXPIRED, S.REJECTED, S.CANCELLED, S.NO_SHOW})

# Timers (scheduled_jobs.job_type)
EXPIRE_HOLD = "EXPIRE_HOLD"
APPROVAL_TIMEOUT = "APPROVAL_TIMEOUT"
MARK_NO_SHOW = "MARK_NO_SHOW"
AUTO_COMPLETE = "AUTO_COMPLETE"


@dataclass(frozen=True, slots=True)
class Actor:
    kind: str  # ActorKind
    membership_id: UUID | None = None
    # True when the actor acts as staff (e.g. cancel_any): member-only deadlines don't apply.
    privileged: bool = False

    @classmethod
    def system(cls) -> "Actor":
        return cls(kind=ActorKind.SYSTEM, privileged=True)

    def as_event_actor(self) -> dict[str, str]:
        if self.kind == ActorKind.USER and self.membership_id:
            return events.user_actor(self.membership_id)
        return events.SYSTEM


@dataclass(frozen=True, slots=True)
class Applied:
    """The policy the booking was made under (policy_versions row it points at), and what
    the rules decided at submit time (stored in its first transition_log row)."""

    version: int
    body: dict[str, Any]
    rule_set_version: int = 0
    needs_approval: bool = False
    trace: tuple[dict[str, Any], ...] = ()

    def rule_record(self) -> list[dict[str, Any]]:
        """transition_log.rule_versions: which rules ran and what they decided."""
        return [
            {
                "ruleSet": self.rule_set_version,
                "needsApproval": self.needs_approval,
                "trace": list(self.trace),
            }
        ]


def _seconds(body: dict[str, Any], key: str) -> timedelta:
    return timedelta(seconds=int(body.get(key, 0)))


def check_in_window(booking: Booking, body: dict[str, Any]) -> tuple[datetime, datetime]:
    opens = booking.start_at - _seconds(body, "checkin_open_before_seconds")
    closes = (
        booking.start_at + _seconds(body, "no_show_after_seconds")
        if body.get("checkin_required")
        else booking.end_at
    )
    return opens, closes


def cancel_deadline(booking: Booking, body: dict[str, Any]) -> datetime:
    return booking.start_at - _seconds(body, "cancel_allowed_until_seconds")


def _guard(booking: Booking, move: str, actor: Actor, applied: Applied, now: datetime) -> None:
    if move == "check_in":
        opens, closes = check_in_window(booking, applied.body)
        if not opens <= now < closes:
            raise InvalidTransition(
                f"Check-in is open from {opens.isoformat()} to {closes.isoformat()}."
            )
    if (
        move == "complete"
        and booking.status == S.CONFIRMED
        and (applied.body.get("checkin_required") or actor.kind != ActorKind.SYSTEM)
    ):
        raise InvalidTransition("A confirmed booking completes by itself at its end.")
    if move == "cancel" and not actor.privileged:
        deadline = cancel_deadline(booking, applied.body)
        if now > deadline:
            raise InvalidTransition(f"Cancellation was allowed until {deadline.isoformat()}.")


def _open_allocations(booking: Booking) -> Any:
    return BookingAllocation.objects.filter(booking=booking, closed_at__isnull=True)


def _effects(booking: Booking, to: str, applied: Applied, now: datetime) -> None:
    body = applied.body
    record = {"object_code": "booking", "record_id": booking.id}
    if to == S.AWAITING_PAYMENT:
        expires = now + _seconds(body, "hold_ttl_seconds")
        _open_allocations(booking).update(effect=AllocationEffect.HOLD, hold_expires_at=expires)
        schedule_job(tenant_id=booking.tenant_id, job_type=EXPIRE_HOLD, run_at=expires, **record)
    elif to == S.PENDING_APPROVAL:
        _open_allocations(booking).update(effect=AllocationEffect.HOLD)
        # Nobody can approve a booking that has already started.
        schedule_job(
            tenant_id=booking.tenant_id,
            job_type=APPROVAL_TIMEOUT,
            run_at=booking.start_at,
            **record,
        )
    elif to == S.CONFIRMED:
        _open_allocations(booking).update(effect=AllocationEffect.LOCK, hold_expires_at=None)
        cancel_jobs(job_types=[EXPIRE_HOLD, APPROVAL_TIMEOUT], **record)
        if body.get("checkin_required"):
            schedule_job(
                tenant_id=booking.tenant_id,
                job_type=MARK_NO_SHOW,
                run_at=booking.start_at + _seconds(body, "no_show_after_seconds"),
                **record,
            )
        else:
            schedule_job(
                tenant_id=booking.tenant_id,
                job_type=AUTO_COMPLETE,
                run_at=booking.end_at + _seconds(body, "buffer_after_seconds"),
                **record,
            )
    elif to == S.CHECKED_IN:
        cancel_jobs(job_types=[MARK_NO_SHOW], **record)
        # After the buffer, so cleaning time after the booking stays blocked.
        schedule_job(
            tenant_id=booking.tenant_id,
            job_type=AUTO_COMPLETE,
            run_at=booking.end_at + _seconds(body, "buffer_after_seconds"),
            **record,
        )
    if to in TERMINAL:
        _open_allocations(booking).update(closed_at=now, close_reason=to)
        cancel_jobs(**record)


_TIMESTAMPS = {
    S.CONFIRMED: "confirmed_at",
    S.CHECKED_IN: "checked_in_at",
    S.COMPLETED: "checked_out_at",
    S.CANCELLED: "cancelled_at",
}


def transition(
    booking: Booking,
    move: str,
    *,
    actor: Actor,
    applied: Applied,
    to: str | None = None,
    reason_code: str | None = None,
    note: str | None = None,
) -> Booking:
    """Apply one move. `booking.status` None means the booking is being submitted; its row
    is inserted here. Must run inside the caller's transaction."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("transition() must run inside a transaction.")
    current = booking.status or SUBMITTED
    targets = MOVES.get((current, move))
    if not targets:
        raise InvalidTransition(f"Cannot {move.replace('_', ' ')} a booking that is {current}.")
    if to is None:
        if len(targets) != 1:
            raise ValueError(f"Move {move} from {current} needs an explicit target.")
        (to,) = targets
    elif to not in targets:
        raise InvalidTransition(f"{move} cannot lead from {current} to {to}.")

    now = timezone.now()
    _guard(booking, move, actor, applied, now)

    booking.status = to
    if to in _TIMESTAMPS:
        setattr(booking, _TIMESTAMPS[to], now)
    if to == S.CANCELLED:
        booking.cancelled_by_membership_id = actor.membership_id
        booking.cancel_reason_code = reason_code
    booking.save()  # insert on submit, update otherwise

    _effects(booking, to, applied, now)

    TransitionLog.objects.create(
        tenant_id=booking.tenant_id,
        object_code="booking",
        record_id=booking.id,
        action=move.upper(),
        from_status=None if current == SUBMITTED else current,
        to_status=to,
        actor_kind=actor.kind,
        actor_membership_id=actor.membership_id,
        reason_code=reason_code,
        note=note,
        policy_version_id=booking.policy_version_id,
        rule_versions=applied.rule_record()
        if current == SUBMITTED
        else [{"ruleSet": applied.rule_set_version}],
        request_id=current_request_id(),
        at=now,
    )
    events.emit_event(
        tenant_id=booking.tenant_id,
        name=EVENT_NAMES[to],
        subject_type="booking",
        subject_id=booking.id,
        actor=actor.as_event_actor(),
        changes={"status": {"from": None if current == SUBMITTED else current, "to": to}},
        config_versions={"flowConfig": applied.version, "ruleSet": applied.rule_set_version},
        data={"reason": reason_code} if reason_code else None,
    )
    return booking
