"""Public interface of the booking module: the pipeline and the lifecycle actions.

create_booking() runs the seven fixed steps of docs/domain/booking.md:
  1 validate request   2 availability   3 eligibility   4 limits   5 approval   6 price
  7 save and start the lifecycle
Steps 1-6 only decide (evaluate(), also used by preview_booking() as a dry run); only
step 7 writes.
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from kernel import permissions as perms
from kernel.access import Access, require_perm
from kernel.db import DEADLOCK_DETECTED, sqlstate, violated_constraint
from kernel.errors import (
    BookingDenied,
    Forbidden,
    InvalidTransition,
    NotFound,
    SlotTaken,
    ValidationFailed,
)
from kernel.models import ActorKind, TransitionLog
from modules.availability import service as availability
from modules.booking import lifecycle as lc
from modules.booking.lifecycle import Actor, Applied, transition
from modules.booking.models import (
    OPEN_STATUSES,
    AllocationEffect,
    Booking,
    BookingAllocation,
    BookingChannel,
)
from modules.booking.models import BookingStatus as S
from modules.config import service as config
from modules.payments import service as payments
from modules.resources import service as resources
from modules.rules import service as rules
from modules.tenancy import service as tenancy
from modules.users import service as users

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
# Bookings that count towards quotas: everything except the ones that never happened.
_COUNTED = (*OPEN_STATUSES, S.COMPLETED, S.NO_SHOW)


def _public_code() -> str:
    return "BK-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


def _buffers(body: dict[str, Any]) -> tuple[timedelta, timedelta]:
    return (
        timedelta(seconds=body.get("buffer_before_seconds", 0)),
        timedelta(seconds=body.get("buffer_after_seconds", 0)),
    )


def _user_actor(access: Access, *, privileged: bool = False) -> Actor:
    return Actor(kind=ActorKind.USER, membership_id=access.membership_id, privileged=privileged)


# ---------- the pipeline ----------


@dataclass(frozen=True, slots=True)
class BookingRequest:
    resource_id: UUID
    start: datetime
    end: datetime
    custom_field_values: dict[str, Any]
    member_id: UUID | None = None


def usage_of(*, member_id: UUID, start: datetime, tz: ZoneInfo) -> dict[str, dict[str, int]]:
    """What the member already has on the booking's local day and ISO week (rule context
    `usage`, used by quota rules)."""
    local = start.astimezone(tz)
    day = local.date()
    week_start = day - timedelta(days=day.weekday())
    week_end = week_start + timedelta(days=7)
    rows = Booking.objects.filter(
        booker_membership_id=member_id,
        status__in=_COUNTED,
        local_date__gte=week_start,
        local_date__lt=week_end,
    ).values_list("local_date", "start_at", "end_at")
    out = {"day": {"bookings": 0, "minutes": 0}, "week": {"bookings": 0, "minutes": 0}}
    for local_date, s, e in rows:
        minutes = int((e - s).total_seconds() // 60)
        out["week"]["bookings"] += 1
        out["week"]["minutes"] += minutes
        if local_date == day:
            out["day"]["bookings"] += 1
            out["day"]["minutes"] += minutes
    return out


def _rule_context(
    *,
    req: BookingRequest,
    resource: Any,
    resource_type_key: str,
    member_id: UUID,
    groups: list[str],
    tz: ZoneInfo,
    now: datetime,
) -> dict[str, Any]:
    """The fixed rule context (docs/domain/rules.md): booking, resource, user, time, usage."""
    local_start = req.start.astimezone(tz)
    return {
        "booking": {
            "start": req.start.isoformat(),
            "end": req.end.isoformat(),
            "durationMinutes": int((req.end - req.start).total_seconds() // 60),
            "startsInDays": (local_start.date() - now.astimezone(tz).date()).days,
            "customFieldValues": req.custom_field_values,
        },
        "resource": {
            "id": str(resource.id),
            "type": resource_type_key,
            "siteId": str(resource.location_id),
            "customFieldValues": resource.attributes,
        },
        "user": {"id": str(member_id), "groups": groups},
        "time": {
            "now": now.isoformat(),
            "weekday": local_start.weekday(),
            "hour": local_start.hour,
            "minute": local_start.minute,
        },
        "usage": usage_of(member_id=member_id, start=req.start, tz=tz),
    }


def _policy_limits(
    req: BookingRequest, body: dict[str, Any], now: datetime
) -> list[dict[str, str]]:
    """Step 4 from the resource type's policy. ruleId names the setting that said no."""
    reasons: list[dict[str, str]] = []
    duration = (req.end - req.start).total_seconds()
    if req.start < now + timedelta(seconds=body["lead_time_min_seconds"]):
        reasons.append(
            {"ruleId": "policy.lead_time_min_seconds", "message": "This start time is too soon."}
        )
    if req.start > now + timedelta(days=body["booking_window_days"]):
        reasons.append(
            {
                "ruleId": "policy.booking_window_days",
                "message": f"Bookings open {body['booking_window_days']} days ahead.",
            }
        )
    if duration < body["min_duration_seconds"]:
        reasons.append(
            {
                "ruleId": "policy.min_duration_seconds",
                "message": f"At least {body['min_duration_seconds'] // 60} minutes.",
            }
        )
    if duration > body["max_duration_seconds"]:
        reasons.append(
            {
                "ruleId": "policy.max_duration_seconds",
                "message": f"At most {body['max_duration_seconds'] // 60} minutes.",
            }
        )
    return reasons


def _check_slot_alignment(req: BookingRequest, slot_minutes: int | None, tz: ZoneInfo) -> None:
    if not slot_minutes:
        return
    local = req.start.astimezone(tz)
    minutes = local.hour * 60 + local.minute
    if local.second or local.microsecond or minutes % slot_minutes:
        raise ValidationFailed.one("start", f"Must start on a {slot_minutes}-minute boundary.")
    if (req.end - req.start).total_seconds() % (slot_minutes * 60):
        raise ValidationFailed.one("end", f"Length must be a multiple of {slot_minutes} minutes.")


@dataclass(slots=True)
class Evaluation:
    """Everything steps 1-6 decided. `denied` set means the pipeline stopped there."""

    resource: Any
    member_id: UUID
    tz: ZoneInfo
    policy: Any
    schema_id: UUID | None
    rule_set_version: int
    needs_approval: bool = False
    amount_minor: int = 0
    price_breakdown: dict[str, Any] = field(default_factory=dict)
    currency: str = "VND"
    denied: list[dict[str, str]] | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)

    @property
    def applied(self) -> Applied:
        return Applied(
            version=self.policy.version,
            body=self.policy.body,
            rule_set_version=self.rule_set_version,
            needs_approval=self.needs_approval,
            trace=tuple(self.trace),
        )

    @property
    def requires_payment(self) -> bool:
        return payments.payment_required(
            policy_body=self.policy.body, amount_minor=self.amount_minor
        )

    @property
    def first_status(self) -> str:
        if self.requires_payment:
            return S.AWAITING_PAYMENT
        return S.PENDING_APPROVAL if self.needs_approval else S.CONFIRMED


def evaluate(*, access: Access, req: BookingRequest, now: datetime) -> Evaluation:
    """Pipeline steps 1-6. Raises ValidationFailed/Forbidden for bad input; a rule or
    setting saying no is returned in `denied`, not raised, so preview can show it."""
    resource = resources.get_resource(req.resource_id)
    location = resource.location
    resource_type = resource.resource_type
    tz = ZoneInfo(location.timezone)

    # Who is it for?
    member_id = req.member_id or access.membership_id
    if member_id != access.membership_id:
        require_perm(access, perms.BOOKING_CREATE_FOR_OTHERS, location.id)
        if not users.membership_exists(tenant_id=access.tenant_id, membership_id=member_id):
            raise ValidationFailed.one("memberId", "No active member with this id.")
    else:
        require_perm(access, perms.BOOKING_CREATE, location.id)

    # 1. Validate the request.
    if req.end <= req.start:
        raise ValidationFailed.one("end", "Must be after start.")
    _check_slot_alignment(req, resource_type.slot_minutes, tz)
    schema_id, _ = config.validate_values(
        resource_type_id=resource_type.id, scope="booking", values=req.custom_field_values
    )
    policy = config.get_policy(resource_type.current_policy_version_id)
    body = policy.body
    rule_list, rule_set_version = rules.published_rules(
        location_id=location.id, resource_type_key=resource_type.code, resource_id=resource.id
    )
    ev = Evaluation(
        resource=resource,
        member_id=member_id,
        tz=tz,
        policy=policy,
        schema_id=schema_id,
        rule_set_version=rule_set_version,
        currency=tenancy.tenant_currency(access.tenant_id),
    )

    # 2. Availability: status, open hours and blackouts. Overlaps are refused by the database.
    if resource.status != "ACTIVE":
        ev.denied = [{"ruleId": "resource.status", "message": "Not bookable right now."}]
        return ev
    ref = availability.ResourceRef(id=resource.id, location_id=location.id)
    if not availability.is_open(
        resource=ref, timezone_name=location.timezone, start=req.start, end=req.end
    ):
        ev.denied = [{"ruleId": "availability.hours", "message": "Closed at this time."}]
        return ev

    # 3-5. Rules by stage; the first stage that says no stops the pipeline.
    ctx = _rule_context(
        req=req,
        resource=resource,
        resource_type_key=resource_type.code,
        member_id=member_id,
        groups=users.role_codes_of(membership_id=member_id),
        tz=tz,
        now=now,
    )
    eligibility = rules.decide(rule_list, "eligibility", ctx)
    ev.trace += [{"stage": "eligibility", **t} for t in eligibility.trace]
    if not eligibility.allowed:
        ev.denied = eligibility.denied
        return ev
    limits = rules.decide(rule_list, "limits", ctx)
    ev.trace += [{"stage": "limits", **t} for t in limits.trace]
    limit_reasons = _policy_limits(req, body, now) + limits.denied
    if limit_reasons:
        ev.denied = limit_reasons
        return ev
    approval = rules.decide(rule_list, "approval", ctx)
    ev.trace += [{"stage": "approval", **t} for t in approval.trace]
    if not approval.allowed:
        ev.denied = approval.denied
        return ev
    ev.needs_approval = bool(body["requires_approval"] or approval.require_approval)

    # 6. Price.
    minutes = int((req.end - req.start).total_seconds() // 60)
    ev.amount_minor, ev.price_breakdown = payments.quote(policy_body=body, minutes=minutes)
    return ev


@transaction.atomic
def create_booking(
    *, access: Access, req: BookingRequest, channel: str = BookingChannel.WEB
) -> Booking:
    now = timezone.now()
    ev = evaluate(access=access, req=req, now=now)
    if ev.denied:
        raise BookingDenied(ev.denied)
    resource = ev.resource
    resource_type = resource.resource_type

    # 7. Save. The allocation goes first: if the slot is taken, nothing else is written.
    on_behalf = ev.member_id != access.membership_id
    booking = Booking(
        tenant_id=access.tenant_id,
        public_code=_public_code(),
        location_id=resource.location_id,
        resource_id=resource.id,
        resource_type_id=resource_type.id,
        booking_mode=resource_type.booking_mode,
        booker_membership_id=ev.member_id,
        created_by_membership_id=access.membership_id if on_behalf else None,
        channel=BookingChannel.OPERATOR if on_behalf else channel,
        status=None,
        start_at=req.start,
        end_at=req.end,
        local_date=req.start.astimezone(ev.tz).date(),
        policy_version_id=ev.policy.id,
        schema_id=ev.schema_id,
        attributes=req.custom_field_values,
        amount_minor=ev.amount_minor,
        currency=ev.currency,
        price_breakdown=ev.price_breakdown,
    )
    before, after = _buffers(ev.policy.body)
    try:
        with transaction.atomic():
            BookingAllocation.objects.create(
                tenant_id=access.tenant_id,
                booking_id=booking.id,
                resource_id=resource.id,
                booking_mode=resource_type.booking_mode,
                during=(req.start - before, req.end + after),
                effect=AllocationEffect.HOLD,
            )
    except (IntegrityError, OperationalError) as exc:
        # Two racing inserts can each wait on the other's row while checking the exclusion
        # constraint; PostgreSQL then aborts one with a deadlock. Both mean "slot taken".
        if (
            violated_constraint(exc) == "allocations_no_overlap"
            or sqlstate(exc) == DEADLOCK_DETECTED
        ):
            raise SlotTaken("Someone else holds this slot.") from None
        raise

    applied = ev.applied
    actor = _user_actor(access)
    move = {
        S.AWAITING_PAYMENT: "require_payment",
        S.PENDING_APPROVAL: "require_approval",
        S.CONFIRMED: "confirm",
    }[ev.first_status]
    transition(booking, move, actor=actor, applied=applied)
    payments.start_payment(
        tenant_id=access.tenant_id,
        booking_id=booking.id,
        amount_minor=ev.amount_minor,
        currency=ev.currency,
        required=ev.requires_payment,
        expires_at=now + timedelta(seconds=ev.policy.body["hold_ttl_seconds"])
        if ev.requires_payment
        else None,
    )
    return booking


def preview_booking(*, access: Access, req: BookingRequest) -> dict[str, Any]:
    """Dry run of steps 1-6 plus a (non-binding) look at the slot: "would this be allowed?".
    Saves nothing. Bad input still fails with VALIDATION_FAILED."""
    now = timezone.now()
    ev = evaluate(access=access, req=req, now=now)
    before, after = _buffers(ev.policy.body)
    busy = busy_intervals(
        resource_ids=[ev.resource.id], start=req.start - before, end=req.end + after
    )[ev.resource.id]
    flow = config.flow_config_from_body(ev.policy.body)
    return {
        "allowed": ev.denied is None and not busy,
        "status": None if ev.denied else ev.first_status,
        "reasons": ev.denied or [],
        "slotFree": not busy,
        "price": {
            "amountMinor": ev.amount_minor,
            "currency": ev.currency,
            "breakdown": ev.price_breakdown,
        },
        "appliedConfig": {
            "flowConfigVersion": ev.policy.version,
            "ruleSetVersion": ev.rule_set_version,
            **flow,
        },
        "trace": ev.trace,
    }


# ---------- reading ----------


def visible_bookings(access: Access) -> QuerySet[Booking]:
    """Members see their own bookings; staff also see bookings at their locations."""
    scopes = access.locations_for(perms.BOOKING_READ_ALL)
    own = Q(booker_membership_id=access.membership_id)
    if None in scopes:
        return Booking.objects.all()
    if scopes:
        return Booking.objects.filter(own | Q(location_id__in=[s for s in scopes if s]))
    if access.can(perms.BOOKING_READ_OWN):
        return Booking.objects.filter(own)
    return Booking.objects.none()


def list_bookings(*, access: Access, filters: dict[str, Any]) -> QuerySet[Booking]:
    qs = visible_bookings(access)
    for key, column in (
        ("resource_id", "resource_id"),
        ("resource_type_id", "resource_type_id"),
        ("site_id", "location_id"),
        ("member_id", "booker_membership_id"),
        ("status", "status"),
    ):
        if filters.get(key):
            qs = qs.filter(**{column: filters[key]})
    if filters.get("from"):
        qs = qs.filter(end_at__gt=filters["from"])
    if filters.get("to"):
        qs = qs.filter(start_at__lt=filters["to"])
    return qs


def get_booking(*, access: Access, booking_id: UUID, for_update: bool = False) -> Booking:
    qs = visible_bookings(access)
    if for_update:
        qs = qs.select_for_update()
    booking = qs.filter(id=booking_id).first()
    if booking is None:
        raise NotFound("No booking with this id.")
    return booking


@dataclass(frozen=True, slots=True)
class BookingView:
    row: Booking
    applied: Applied
    timezone: str
    history: list[TransitionLog]
    payment: Any = None


def _applied_from(policy: Any, first: TransitionLog | None) -> Applied:
    record = (first.rule_versions or [{}])[0] if first else {}
    return Applied(
        version=policy.version,
        body=policy.body,
        rule_set_version=int(record.get("ruleSet", 0)),
        needs_approval=bool(record.get("needsApproval", policy.body.get("requires_approval"))),
        trace=tuple(record.get("trace", [])),
    )


def describe(rows: list[Booking]) -> list[BookingView]:
    """Gather what the contract's Booking needs: policy, site timezone, history, payment."""
    policies = config.get_policies(list({r.policy_version_id for r in rows}))
    history: dict[UUID, list[TransitionLog]] = {r.id: [] for r in rows}
    for log in TransitionLog.objects.filter(
        object_code="booking", record_id__in=list(history)
    ).order_by("at", "id"):
        history[log.record_id].append(log)
    pays = payments.payments_by_booking([r.id for r in rows])
    zones: dict[UUID, str] = {}
    out = []
    for r in rows:
        if r.location_id not in zones:
            zones[r.location_id] = resources.get_location(r.location_id).timezone
        out.append(
            BookingView(
                row=r,
                applied=_applied_from(
                    policies[r.policy_version_id], history[r.id][0] if history[r.id] else None
                ),
                timezone=zones[r.location_id],
                history=history[r.id],
                payment=pays.get(r.id),
            )
        )
    return out


def busy_intervals(
    *, resource_ids: list[UUID], start: datetime, end: datetime
) -> dict[UUID, list[tuple[datetime, datetime]]]:
    """Open allocations (buffers included) overlapping [start, end), per resource."""
    out: dict[UUID, list[tuple[datetime, datetime]]] = {rid: [] for rid in resource_ids}
    for a in BookingAllocation.objects.filter(
        resource_id__in=resource_ids, closed_at__isnull=True, during__overlap=(start, end)
    ):
        out[a.resource_id].append((a.during.lower, a.during.upper))
    return out


def upcoming_on(
    *, resource_ids: list[UUID], start: datetime | None = None, end: datetime | None = None
) -> list[dict[str, Any]]:
    """Open bookings not yet over on these resources (optionally inside [start, end)), for an
    admin deciding about maintenance or a blackout. Nothing is cancelled automatically."""
    qs = Booking.objects.filter(
        resource_id__in=resource_ids, status__in=OPEN_STATUSES, end_at__gt=timezone.now()
    )
    if start and end:
        qs = qs.filter(start_at__lt=end, end_at__gt=start)
    return [
        {
            "id": str(b.id),
            "publicCode": b.public_code,
            "resourceId": str(b.resource_id),
            "memberId": str(b.booker_membership_id),
            "start": b.start_at.isoformat(),
            "end": b.end_at.isoformat(),
            "status": b.status,
        }
        for b in qs.order_by("start_at")[:200]
    ]


# ---------- lifecycle actions ----------


def _applied(booking: Booking) -> Applied:
    first = (
        TransitionLog.objects.filter(object_code="booking", record_id=booking.id)
        .order_by("at", "id")
        .first()
    )
    return _applied_from(config.get_policy(booking.policy_version_id), first)


def _is_own(access: Access, booking: Booking) -> bool:
    return booking.booker_membership_id == access.membership_id


@transaction.atomic
def approve(*, access: Access, booking_id: UUID) -> Booking:
    booking = get_booking(access=access, booking_id=booking_id, for_update=True)
    require_perm(access, perms.BOOKING_APPROVE, booking.location_id)
    return transition(
        booking, "approve", actor=_user_actor(access, privileged=True), applied=_applied(booking)
    )


@transaction.atomic
def reject(*, access: Access, booking_id: UUID, reason: str) -> Booking:
    booking = get_booking(access=access, booking_id=booking_id, for_update=True)
    require_perm(access, perms.BOOKING_APPROVE, booking.location_id)
    transition(
        booking,
        "reject",
        actor=_user_actor(access, privileged=True),
        applied=_applied(booking),
        reason_code="rejected_by_approver",
        note=reason,
    )
    # Paid upfront and then rejected: the member gets everything back.
    payments.refund_for(
        booking_id=booking.id,
        percent=100,
        reason="rejected",
        membership_id=access.membership_id,
    )
    return booking


def _check_in_perm(access: Access, booking: Booking) -> None:
    if _is_own(access, booking) and access.can(perms.BOOKING_CHECK_IN_OWN, booking.location_id):
        return
    require_perm(access, perms.BOOKING_CHECK_IN_ANY, booking.location_id)


@transaction.atomic
def check_in(*, access: Access, booking_id: UUID) -> Booking:
    booking = get_booking(access=access, booking_id=booking_id, for_update=True)
    _check_in_perm(access, booking)
    return transition(booking, "check_in", actor=_user_actor(access), applied=_applied(booking))


@transaction.atomic
def check_out(*, access: Access, booking_id: UUID) -> Booking:
    """Leave early (API_KICH_BAN.md 6.8): checked_in -> completed, the slot is freed now."""
    booking = get_booking(access=access, booking_id=booking_id, for_update=True)
    _check_in_perm(access, booking)
    return transition(
        booking,
        "complete",
        actor=_user_actor(access),
        applied=_applied(booking),
        reason_code="checked_out",
    )


@transaction.atomic
def cancel(*, access: Access, booking_id: UUID) -> Booking:
    """Members cancel their own bookings until the policy deadline. Staff (cancel_any at the
    booking's site) may cancel anyone's booking, also after that deadline.

    Money: an unpaid hold is voided; a paid booking is refunded by the policy's refund
    rules (staff cancellations refund in full)."""
    booking = get_booking(access=access, booking_id=booking_id, for_update=True)
    staff = access.can(perms.BOOKING_CANCEL_ANY, booking.location_id)
    own = _is_own(access, booking)
    if not staff:
        if not own:
            raise Forbidden("You can only cancel your own bookings.")
        require_perm(access, perms.BOOKING_CANCEL_OWN, booking.location_id)
    applied = _applied(booking)
    reason = "cancelled_by_member" if own else "cancelled_by_staff"
    transition(
        booking,
        "cancel",
        actor=_user_actor(access, privileged=staff),
        applied=applied,
        reason_code=reason,
    )
    payments.expire_pending(booking_id=booking.id, reason="cancelled")
    seconds_before = (booking.start_at - timezone.now()).total_seconds()
    percent = 100 if staff and not own else config.refund_percent(applied.body, seconds_before)
    payments.refund_for(
        booking_id=booking.id,
        percent=percent,
        reason=reason,
        membership_id=access.membership_id,
        rule={"secondsBeforeStart": int(seconds_before)},
    )
    return booking


# ---------- payments (the booking side of it) ----------


def _after_paid(booking: Booking, actor: Actor) -> Booking:
    """awaiting_payment -> pending_approval (if the rules wanted approval) or confirmed."""
    applied = _applied(booking)
    to = S.PENDING_APPROVAL if applied.needs_approval else S.CONFIRMED
    return transition(booking, "paid", to=to, actor=actor, applied=applied)


@transaction.atomic
def mark_paid(*, access: Access, payment_id: UUID, method: str, note: str | None) -> Booking:
    payment = payments.get_payment(payment_id)
    booking = get_booking(access=access, booking_id=payment.booking_id, for_update=True)
    require_perm(access, perms.PAYMENT_MARK_PAID, booking.location_id)
    if booking.status != S.AWAITING_PAYMENT:
        raise InvalidTransition(f"The booking is {booking.status}, not awaiting payment.")
    payments.mark_paid(
        payment_id=payment.id, membership_id=access.membership_id, method=method, note=note
    )
    return _after_paid(booking, _user_actor(access, privileged=True))


@transaction.atomic
def mark_refunded(*, access: Access, refund_id: UUID) -> Any:
    refund = payments.get_refund(refund_id)
    booking = get_booking(access=access, booking_id=refund.payment.booking_id)
    require_perm(access, perms.PAYMENT_REFUND, booking.location_id)
    return payments.mark_refunded(refund_id=refund.id, membership_id=access.membership_id)


@transaction.atomic
def apply_payment_webhook(
    *, gateway: str, raw_body: bytes, signature: str, body: dict[str, Any], tenant_id: UUID
) -> payments.WebhookResult:
    """The tenant is already active (from the URL). The gateway is the actor."""
    result = payments.record_webhook(
        tenant_id=tenant_id, gateway=gateway, raw_body=raw_body, signature=signature, body=body
    )
    if result.outcome != "APPLIED" or result.payment is None:
        return result
    actor = Actor(kind=ActorKind.GATEWAY, privileged=True)
    booking = Booking.objects.select_for_update().get(id=result.payment.booking_id)
    if booking.status == S.AWAITING_PAYMENT:
        if result.kind == "payment.succeeded":
            _after_paid(booking, actor)
        elif result.kind == "payment.failed":
            transition(
                booking,
                "payment_failed",
                actor=actor,
                applied=_applied(booking),
                reason_code="payment_failed",
            )
    return result


# ---------- timers (run by the worker as SYSTEM) ----------


def run_timer(*, booking_id: UUID, job_type: str) -> None:
    """Apply a due timer if the booking is still in the status the timer was set for."""
    booking = Booking.objects.select_for_update().filter(id=booking_id).first()
    if booking is None:
        return
    plan = {
        lc.MARK_NO_SHOW: ((S.CONFIRMED,), "no_show", "no_check_in"),
        lc.AUTO_COMPLETE: ((S.CHECKED_IN, S.CONFIRMED), "complete", None),
        lc.APPROVAL_TIMEOUT: ((S.PENDING_APPROVAL,), "reject", "approval_timeout"),
        lc.EXPIRE_HOLD: ((S.AWAITING_PAYMENT,), "expire", "payment_timeout"),
    }
    expected, move, reason = plan[job_type]
    if booking.status not in expected:
        return  # something else already moved it; the timer is moot
    applied = _applied(booking)
    if (
        booking.status == S.CONFIRMED
        and move == "complete"
        and applied.body.get("checkin_required")
    ):
        return  # check-in was required and never happened: MARK_NO_SHOW handles it
    transition(booking, move, actor=Actor.system(), applied=applied, reason_code=reason)
    if job_type == lc.EXPIRE_HOLD:
        payments.expire_pending(booking_id=booking.id, reason="hold_expired")
    if job_type == lc.APPROVAL_TIMEOUT:
        payments.refund_for(
            booking_id=booking.id, percent=100, reason="approval_timeout", membership_id=None
        )
