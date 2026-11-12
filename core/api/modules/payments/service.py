"""Public interface of the payments module.

Payment is a lifecycle policy, not a pipeline step (docs/domain/booking.md). The resource
type's policy says whether a booking pays upfront (flowConfig.payment.mode). Then:

  submit   -> payment PENDING (session id, expires with the hold)     booking awaiting_payment
  paid     <- gateway webhook or the desk (mark-paid): PAID          booking -> confirmed/approval
  timeout  -> EXPIRED (EXPIRE_HOLD timer)                            booking expired
  cancel   -> refund per policy: refund row PENDING, payment REFUND_PENDING
  refund settled <- webhook or desk: refund SUCCEEDED, payment (PARTIALLY_)REFUNDED

This module never changes a booking: modules/booking/service.py calls it and then moves the
booking with transition(). Every payment status change writes transition_log and one event.
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from kernel.errors import InvalidTransition, NotFound, ValidationFailed
from kernel.history import record_status
from kernel.models import ActorKind
from kernel.uuid7 import uuid7
from modules.events import service as events
from modules.payments.models import (
    Payment,
    PaymentEvent,
    PaymentEventOutcome,
    PaymentStatus,
    Refund,
    RefundStatus,
)

MANUAL = "manual"


# ---------- price (pipeline step 6) ----------


def quote(
    *, policy_body: dict[str, Any], minutes: int, rule_requires: bool = False
) -> tuple[int, dict[str, Any]]:
    """(amount in minor units, breakdown stored on the booking). Free unless the type is
    paid (`payment.mode: upfront`) or a require_payment rule matched; either way the price is
    the resource type's own (`flowConfig.payment.amountMinor`)."""
    if not (policy_body.get("requires_payment") or rule_requires):
        return 0, {}
    price = policy_body.get("price") or {"amount_minor": 0, "per": "booking"}
    unit = int(price["amount_minor"])
    if price["per"] == "hour":
        amount = (unit * minutes + 59) // 60  # round up to a whole minor unit
        return amount, {"per": "hour", "unitAmountMinor": unit, "minutes": minutes}
    return unit, {"per": "booking", "unitAmountMinor": unit}


def payment_required(
    *, policy_body: dict[str, Any], amount_minor: int, rule_requires: bool = False
) -> bool:
    return bool(policy_body.get("requires_payment") or rule_requires) and amount_minor > 0


# ---------- status moves ----------

_EVENTS = {
    PaymentStatus.PENDING: "payment.session_created",
    PaymentStatus.PAID: "payment.paid",
    PaymentStatus.EXPIRED: "payment.expired",
    PaymentStatus.FAILED: "payment.failed",
    PaymentStatus.REFUND_PENDING: "refund.requested",
    PaymentStatus.REFUNDED: "refund.succeeded",
    PaymentStatus.PARTIALLY_REFUNDED: "refund.succeeded",
}


def _move(
    payment: Payment,
    to: str,
    *,
    action: str,
    membership_id: UUID | None,
    actor_kind: str | None = None,
    reason: str | None = None,
    data: dict[str, Any] | None = None,
) -> Payment:
    before = payment.status
    payment.status = to
    payment.save()
    record_status(
        tenant_id=payment.tenant_id,
        object_code="payment",
        record_id=payment.id,
        action=action,
        from_status=before or None,
        to_status=to,
        membership_id=membership_id,
        actor_kind=actor_kind,
        reason_code=reason,
    )
    if to in _EVENTS:
        events.emit_event(
            tenant_id=payment.tenant_id,
            name=_EVENTS[to],
            subject_type="payment",
            subject_id=payment.id,
            actor=events.user_actor(membership_id) if membership_id else events.SYSTEM,
            changes={"status": {"from": before.lower() if before else None, "to": to.lower()}},
            data={"bookingId": str(payment.booking_id), **(data or {})},
        )
    return payment


def start_payment(
    *,
    tenant_id: UUID,
    booking_id: UUID,
    amount_minor: int,
    currency: str,
    required: bool = False,
    expires_at: datetime | None = None,
) -> Payment:
    """Every booking has one payment row: WAIVED when free, PENDING when it pays upfront."""
    if not required:
        return Payment.objects.create(
            tenant_id=tenant_id,
            booking_id=booking_id,
            status=PaymentStatus.WAIVED,
            amount_minor=amount_minor,
            currency=currency,
            gateway="none",
            method="none",
        )
    payment = Payment(
        tenant_id=tenant_id,
        booking_id=booking_id,
        status="",
        amount_minor=amount_minor,
        currency=currency,
        gateway=settings.PAYMENTS["GATEWAY"],
        gateway_session_id=f"sess_{uuid7().hex}",
        expires_at=expires_at,
    )
    # The gateway session itself is opened by a subscriber of payment.session_created.
    return _move(payment, PaymentStatus.PENDING, action="start", membership_id=None)


def payment_of(booking_id: UUID) -> Payment | None:
    return Payment.objects.filter(booking_id=booking_id).first()


def payments_by_booking(booking_ids: list[UUID]) -> dict[UUID, Payment]:
    return {p.booking_id: p for p in Payment.objects.filter(booking_id__in=booking_ids)}


def get_payment(payment_id: UUID, *, for_update: bool = False) -> Payment:
    qs = Payment.objects.select_for_update() if for_update else Payment.objects.all()
    payment = qs.filter(id=payment_id).first()
    if payment is None:
        raise NotFound("No payment with this id.")
    return payment


def _receipt(
    payment: Payment | None,
    *,
    tenant_id: UUID,
    gateway: str,
    event_id: str,
    kind: str,
    payload: dict[str, Any],
    verified: bool,
    outcome: str,
) -> PaymentEvent:
    return PaymentEvent.objects.create(
        tenant_id=tenant_id,
        payment=payment,
        gateway=gateway,
        gateway_event_id=event_id,
        type=kind,
        payload=payload,
        signature_verified=verified,
        outcome=outcome,
        processed_at=timezone.now(),
    )


@transaction.atomic
def mark_paid(*, payment_id: UUID, membership_id: UUID, method: str, note: str | None) -> Payment:
    """The desk took the money (cash, card terminal, bank transfer). Writes a payment_events
    row too, so every payment has a receipt (API_KICH_BAN.md 7.2)."""
    payment = get_payment(payment_id, for_update=True)
    if payment.status != PaymentStatus.PENDING:
        raise InvalidTransition(
            f"Only a pending payment can be marked paid; this one is {payment.status.lower()}."
        )
    _receipt(
        payment,
        tenant_id=payment.tenant_id,
        gateway=MANUAL,
        event_id=f"manual-{uuid7().hex}",
        kind="payment.succeeded",
        payload={"method": method, "note": note or "", "byMembershipId": str(membership_id)},
        verified=True,
        outcome=PaymentEventOutcome.APPLIED,
    )
    payment.method = method
    payment.paid_at = timezone.now()
    payment.gateway_payment_ref = payment.gateway_payment_ref or f"desk-{membership_id}"
    return _move(payment, PaymentStatus.PAID, action="mark_paid", membership_id=membership_id)


def expire_pending(*, booking_id: UUID, reason: str) -> Payment | None:
    """The hold ran out, or the booking ended before it was paid."""
    payment = Payment.objects.select_for_update().filter(booking_id=booking_id).first()
    if payment is None or payment.status != PaymentStatus.PENDING:
        return payment
    payment.failure_code = reason
    return _move(payment, PaymentStatus.EXPIRED, action="expire", membership_id=None, reason=reason)


def refund_for(
    *,
    booking_id: UUID,
    percent: int,
    reason: str,
    membership_id: UUID | None,
    rule: dict[str, Any] | None = None,
) -> Refund | None:
    """Refund `percent` of a PAID payment (cancel, reject). Nothing to refund -> None."""
    payment = Payment.objects.select_for_update().filter(booking_id=booking_id).first()
    if payment is None or payment.status != PaymentStatus.PAID:
        return None
    amount = payment.amount_minor * percent // 100
    if amount <= 0:
        return None
    refund = Refund.objects.create(
        tenant_id=payment.tenant_id,
        payment=payment,
        amount_minor=amount,
        reason_code=reason,
        applied_rule={"percent": percent, **(rule or {})},
        requested_by_membership_id=membership_id,
    )
    _move(
        payment,
        PaymentStatus.REFUND_PENDING,
        action="refund",
        membership_id=membership_id,
        reason=reason,
        data={"refundId": str(refund.id), "amountMinor": amount},
    )
    return refund


def get_refund(refund_id: UUID) -> Refund:
    refund = (
        Refund.objects.select_for_update().select_related("payment").filter(id=refund_id).first()
    )
    if refund is None:
        raise NotFound("No refund with this id.")
    return refund


def _settle_refund(refund: Refund, *, membership_id: UUID | None, actor_kind: str | None) -> Refund:
    if refund.status != RefundStatus.PENDING:
        raise InvalidTransition(f"This refund is already {refund.status.lower()}.")
    refund.status = RefundStatus.SUCCEEDED
    refund.completed_at = timezone.now()
    refund.save(update_fields=["status", "completed_at", "updated_at"])
    payment = Payment.objects.select_for_update().get(id=refund.payment_id)
    payment.refunded_minor += refund.amount_minor
    to = (
        PaymentStatus.REFUNDED
        if payment.refunded_minor >= payment.amount_minor
        else PaymentStatus.PARTIALLY_REFUNDED
    )
    _move(
        payment,
        to,
        action="refund_succeeded",
        membership_id=membership_id,
        actor_kind=actor_kind,
        data={"refundId": str(refund.id), "amountMinor": refund.amount_minor},
    )
    return refund


@transaction.atomic
def mark_refunded(*, refund_id: UUID, membership_id: UUID) -> Refund:
    """The desk paid the money back (manual gateway)."""
    refund = get_refund(refund_id)
    _receipt(
        refund.payment,
        tenant_id=refund.tenant_id,
        gateway=MANUAL,
        event_id=f"manual-{uuid7().hex}",
        kind="refund.succeeded",
        payload={"refundId": str(refund.id), "byMembershipId": str(membership_id)},
        verified=True,
        outcome=PaymentEventOutcome.APPLIED,
    )
    return _settle_refund(refund, membership_id=membership_id, actor_kind=None)


# ---------- gateway webhooks ----------

WEBHOOK_TYPES = frozenset(
    {"payment.succeeded", "payment.failed", "refund.succeeded", "refund.failed"}
)
_PAYLOAD_KEYS = ("eventId", "type", "sessionId", "refundId", "amountMinor", "paymentRef", "reason")


def sign(raw_body: bytes) -> str:
    """HMAC-SHA256 of the raw body with PAYMENT_WEBHOOK_SECRET: what the mock gateway sends in
    X-Signature. A real gateway gets its own verifier here."""
    secret = settings.PAYMENTS["WEBHOOK_SECRET"].encode()
    return hmac.new(secret, raw_body, hashlib.sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class WebhookResult:
    outcome: str
    kind: str
    payment: Payment | None = None


def record_webhook(
    *, tenant_id: UUID, gateway: str, raw_body: bytes, signature: str, body: dict[str, Any]
) -> WebhookResult:
    """Store first, then check (API_KICH_BAN.md 7.1). The caller moves the booking for
    payment.succeeded / payment.failed results with outcome APPLIED."""
    if gateway not in settings.PAYMENTS["WEBHOOK_GATEWAYS"]:
        raise NotFound("Unknown payment gateway.")
    if not settings.PAYMENTS["WEBHOOK_SECRET"]:
        raise ValidationFailed.one("gateway", "Webhooks are not configured (no secret).")
    event_id = str(body.get("eventId") or "")
    kind = str(body.get("type") or "")
    if not event_id:
        raise ValidationFailed.one("eventId", "Required.")
    payload = {k: body[k] for k in _PAYLOAD_KEYS if k in body}
    verified = hmac.compare_digest(sign(raw_body), signature or "")
    try:
        with transaction.atomic():
            receipt = _receipt(
                None,
                tenant_id=tenant_id,
                gateway=gateway,
                event_id=event_id,
                kind=kind,
                payload=payload,
                verified=verified,
                outcome=PaymentEventOutcome.IGNORED,
            )
    except IntegrityError:
        return WebhookResult(outcome=PaymentEventOutcome.DUPLICATE, kind=kind)
    if not verified or kind not in WEBHOOK_TYPES:
        return WebhookResult(outcome=PaymentEventOutcome.IGNORED, kind=kind)

    def finish(outcome: str, payment: Payment | None) -> WebhookResult:
        receipt.outcome = outcome
        receipt.payment = payment
        receipt.save(update_fields=["outcome", "payment", "updated_at"])
        if outcome == PaymentEventOutcome.NEEDS_RECONCILIATION:
            events.emit_event(
                tenant_id=tenant_id,
                name="payment.reconciliation_needed",
                subject_type="payment",
                subject_id=payment.id if payment else receipt.id,
                actor={"type": "system"},
                data={"gatewayEventId": event_id, "type": kind},
            )
        return WebhookResult(outcome=outcome, kind=kind, payment=payment)

    if kind.startswith("refund."):
        refund = Refund.objects.select_for_update().filter(id=_uuid(body.get("refundId"))).first()
        if refund is None or refund.status != RefundStatus.PENDING:
            return finish(
                PaymentEventOutcome.NEEDS_RECONCILIATION, refund.payment if refund else None
            )
        if kind == "refund.succeeded":
            refund.gateway_refund_id = body.get("paymentRef") or refund.gateway_refund_id
            _settle_refund(refund, membership_id=None, actor_kind=ActorKind.GATEWAY)
        else:
            refund.status = RefundStatus.FAILED
            refund.failure_code = str(body.get("reason") or "gateway_failed")
            refund.completed_at = timezone.now()
            refund.save(update_fields=["status", "failure_code", "completed_at", "updated_at"])
        return finish(PaymentEventOutcome.APPLIED, refund.payment)

    payment = (
        Payment.objects.select_for_update()
        .filter(gateway=gateway, gateway_session_id=body.get("sessionId"))
        .first()
    )
    if payment is None or payment.status != PaymentStatus.PENDING:
        # Paid after the hold expired, or for a booking already gone: a person decides.
        return finish(PaymentEventOutcome.NEEDS_RECONCILIATION, payment)
    if kind == "payment.succeeded":
        if int(body.get("amountMinor", -1)) != payment.amount_minor:
            return finish(PaymentEventOutcome.NEEDS_RECONCILIATION, payment)
        payment.paid_at = timezone.now()
        payment.gateway_payment_ref = body.get("paymentRef")
        payment.method = payment.method or "gateway"
        _move(
            payment,
            PaymentStatus.PAID,
            action="paid",
            membership_id=None,
            actor_kind=ActorKind.GATEWAY,
        )
    else:
        payment.failure_code = str(body.get("reason") or "gateway_failed")
        _move(
            payment,
            PaymentStatus.FAILED,
            action="failed",
            membership_id=None,
            actor_kind=ActorKind.GATEWAY,
        )
    return finish(PaymentEventOutcome.APPLIED, payment)


def _uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


# ---------- reading ----------


def refunds_of(payment_id: UUID) -> list[Refund]:
    return list(Refund.objects.filter(payment_id=payment_id).order_by("requested_at"))


def events_of(payment_id: UUID) -> list[PaymentEvent]:
    return list(PaymentEvent.objects.filter(payment_id=payment_id).order_by("received_at"))


def reconciliation_queue() -> list[PaymentEvent]:
    return list(
        PaymentEvent.objects.filter(outcome=PaymentEventOutcome.NEEDS_RECONCILIATION).order_by(
            "-received_at"
        )
    )
