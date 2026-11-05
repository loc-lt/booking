from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models
from django.db.models import F, Func, Q, Value

from kernel.models import TenantModel


class BookingStatus(models.TextChoices):
    """The nine statuses of docs/domain/booking.md, stored exactly as the contract names
    them. `submitted` is the entry point, never stored. Change only through transition()."""

    AWAITING_PAYMENT = "awaiting_payment"
    PENDING_APPROVAL = "pending_approval"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    EXPIRED = "expired"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


OPEN_STATUSES = (
    BookingStatus.AWAITING_PAYMENT,
    BookingStatus.PENDING_APPROVAL,
    BookingStatus.CONFIRMED,
    BookingStatus.CHECKED_IN,
)


class BookingChannel(models.TextChoices):
    WEB = "web"
    OPERATOR = "operator"
    API = "api"


class Booking(TenantModel):
    """A request for one resource over [start_at, end_at). The double-booking guard is on
    booking_allocations, not here."""

    public_code = models.TextField()
    location = models.ForeignKey("resources.Location", on_delete=models.PROTECT, related_name="+")
    resource = models.ForeignKey("resources.Resource", on_delete=models.PROTECT, related_name="+")
    resource_type = models.ForeignKey(
        "resources.ResourceType", on_delete=models.PROTECT, related_name="+"
    )
    booking_mode = models.TextField()
    booker_membership = models.ForeignKey(
        "users.Membership", on_delete=models.PROTECT, related_name="+"
    )
    created_by_membership = models.ForeignKey(
        "users.Membership", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    channel = models.TextField(choices=BookingChannel.choices, default=BookingChannel.WEB)
    status = models.TextField(choices=BookingStatus.choices)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    during = models.GeneratedField(
        expression=Func(F("start_at"), F("end_at"), Value("[)"), function="tstzrange"),
        output_field=DateTimeRangeField(),
        db_persist=True,
    )
    local_date = models.DateField()
    party_size = models.IntegerField(default=1)
    policy_version = models.ForeignKey(
        "config.PolicyVersion", on_delete=models.PROTECT, related_name="+"
    )
    schema = models.ForeignKey(
        "config.ObjectSchemaVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    attributes = models.JSONField(default=dict)
    amount_minor = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3)
    price_breakdown = models.JSONField(default=dict)
    rescheduled_from = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by_membership = models.ForeignKey(
        "users.Membership", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    cancel_reason_code = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "bookings"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "public_code"], name="bookings_public_code"),
            models.UniqueConstraint(fields=["tenant", "id"], name="bookings_tenant_id"),
            models.CheckConstraint(condition=Q(end_at__gt=F("start_at")), name="bookings_order"),
            models.CheckConstraint(condition=Q(amount_minor__gte=0), name="bookings_amount"),
        ]
        indexes = [
            models.Index(fields=["tenant", "resource", "start_at"], name="bookings_resource_time"),
            models.Index(
                F("tenant"), F("booker_membership"), F("start_at").desc(), name="bookings_booker"
            ),
            models.Index(fields=["tenant", "location", "start_at"], name="bookings_location_time"),
            models.Index(
                fields=["tenant", "status", "start_at"],
                condition=Q(status__in=OPEN_STATUSES),
                name="bookings_open",
            ),
        ]


class AllocationEffect(models.TextChoices):
    HOLD = "HOLD"  # temporary, until approved/paid or expired
    LOCK = "LOCK"  # firm


class BookingAllocation(TenantModel):
    """The part of a booking that occupies a resource. `during` includes the buffers.

    allocations_no_overlap (see migration) makes PostgreSQL refuse a second open EXCLUSIVE
    allocation overlapping the same resource: the API returns SLOT_TAKEN.
    """

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="allocations")
    resource = models.ForeignKey("resources.Resource", on_delete=models.PROTECT, related_name="+")
    booking_mode = models.TextField()
    during = DateTimeRangeField()
    effect = models.TextField(choices=AllocationEffect.choices)
    seats = models.IntegerField(default=1)
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    close_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "booking_allocations"
        constraints = [
            models.CheckConstraint(condition=Q(seats__gt=0), name="allocations_seats"),
        ]
        indexes = [
            models.Index(fields=["tenant", "booking"], name="allocations_booking"),
        ]
