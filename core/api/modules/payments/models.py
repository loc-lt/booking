from django.db import models
from django.utils import timezone

from kernel.models import TenantModel


class PaymentStatus(models.TextChoices):
    REQUIRES_PAYMENT = "REQUIRES_PAYMENT"
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"
    WAIVED = "WAIVED"


class Payment(TenantModel):
    """Money, tracked apart from the booking status. One booking, one payment.
    Free resource types: WAIVED. Upfront payment: PENDING until a gateway webhook or the
    desk (mark-paid) settles it, EXPIRED when the hold runs out."""

    booking = models.OneToOneField(
        "booking.Booking", on_delete=models.PROTECT, related_name="payment"
    )
    status = models.TextField(choices=PaymentStatus.choices)
    method = models.TextField(null=True, blank=True)
    amount_minor = models.BigIntegerField()
    refunded_minor = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3)
    gateway = models.TextField()
    gateway_session_id = models.TextField(null=True, blank=True)
    gateway_payment_ref = models.TextField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.TextField(null=True, blank=True)
    attributes = models.JSONField(default=dict)
    schema = models.ForeignKey(
        "config.ObjectSchemaVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "payments"
        constraints = [
            models.UniqueConstraint(
                fields=["gateway", "gateway_session_id"], name="payments_gateway_session"
            ),
            models.UniqueConstraint(fields=["tenant", "id"], name="payments_tenant_id"),
            models.CheckConstraint(condition=models.Q(amount_minor__gte=0), name="payments_amount"),
            models.CheckConstraint(
                condition=models.Q(refunded_minor__lte=models.F("amount_minor")),
                name="payments_refunded",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "status", "created_at"], name="payments_status"),
        ]


class PaymentEventOutcome(models.TextChoices):
    APPLIED = "APPLIED"
    DUPLICATE = "DUPLICATE"
    IGNORED = "IGNORED"  # bad signature, unknown type, nothing to change
    NEEDS_RECONCILIATION = "NEEDS_RECONCILIATION"  # money arrived for a booking that is gone


class PaymentEvent(TenantModel):
    """Every message from a gateway, and every desk payment, stored before it is applied.
    (gateway, gateway_event_id) is unique, so a resent webhook takes effect once."""

    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, null=True, blank=True, related_name="events"
    )
    gateway = models.TextField()
    gateway_event_id = models.TextField()
    type = models.TextField()
    payload = models.JSONField()  # allowlisted keys only: no card numbers, no secrets
    signature_verified = models.BooleanField()
    outcome = models.TextField(choices=PaymentEventOutcome.choices)
    received_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_events"
        constraints = [
            models.UniqueConstraint(
                fields=["gateway", "gateway_event_id"], name="payment_events_gateway_event"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "payment"], name="payment_events_payment"),
            models.Index(
                fields=["outcome"],
                condition=models.Q(outcome="NEEDS_RECONCILIATION"),
                name="payment_events_reconcile",
            ),
        ]


class RefundStatus(models.TextChoices):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class Refund(TenantModel):
    """One row per refund; a payment can be refunded in parts."""

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    amount_minor = models.BigIntegerField()
    status = models.TextField(choices=RefundStatus.choices, default=RefundStatus.PENDING)
    reason_code = models.TextField()
    applied_rule = models.JSONField(null=True, blank=True)
    gateway_refund_id = models.TextField(null=True, blank=True, unique=True)
    requested_by_membership_id = models.UUIDField(null=True, blank=True)
    requested_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "refunds"
        constraints = [
            models.CheckConstraint(condition=models.Q(amount_minor__gt=0), name="refunds_amount"),
        ]
        indexes = [models.Index(fields=["tenant", "payment"], name="refunds_payment")]
