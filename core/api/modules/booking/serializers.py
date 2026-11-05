"""Request validation and the contract's Booking shape."""

from typing import Any
from zoneinfo import ZoneInfo

from rest_framework import serializers

from kernel.serializers import AwareDateTimeField
from modules.booking.models import BookingStatus
from modules.booking.service import BookingView
from modules.config.service import flow_config_from_body


class CreateBookingRequest(serializers.Serializer):
    resourceId = serializers.UUIDField()
    memberId = serializers.UUIDField(required=False)
    start = AwareDateTimeField()
    end = AwareDateTimeField()
    customFieldValues = serializers.DictField(default=dict)


class PreviewBookingRequest(CreateBookingRequest):
    pass


class RejectBookingRequest(serializers.Serializer):
    reason = serializers.CharField(min_length=1, max_length=1000)


class BookingListQuery(serializers.Serializer):
    resourceId = serializers.UUIDField(required=False)
    resourceTypeId = serializers.UUIDField(required=False)
    siteId = serializers.UUIDField(required=False)
    memberId = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(choices=BookingStatus.values, required=False)
    # "from" is a Python keyword, so the field is declared below.
    to = AwareDateTimeField(required=False)


BookingListQuery._declared_fields["from"] = AwareDateTimeField(required=False)


def payment_summary(p: Any) -> dict[str, Any] | None:
    if p is None:
        return None
    return {
        "id": str(p.id),
        "status": p.status.lower(),
        "amountMinor": p.amount_minor,
        "refundedMinor": p.refunded_minor,
        "currency": p.currency,
        "expiresAt": p.expires_at.isoformat() if p.expires_at else None,
    }


def booking_json(view: BookingView) -> dict[str, Any]:
    b = view.row
    tz = ZoneInfo(view.timezone)
    flow = flow_config_from_body(view.applied.body)
    history = []
    for log in view.history:
        entry: dict[str, Any] = {
            "toStatus": log.to_status,
            "occurredAt": log.at.isoformat(),
            "actor": (
                {"type": "user", "id": str(log.actor_membership_id)}
                if log.actor_membership_id
                else {"type": "system"}
            ),
        }
        if log.from_status:
            entry["fromStatus"] = log.from_status
        history.append(entry)
    return {
        "id": str(b.id),
        "resourceId": str(b.resource_id),
        "resourceTypeId": str(b.resource_type_id),
        "siteId": str(b.location_id),
        "memberId": str(b.booker_membership_id),
        # Start and end in the site's own offset, as in the contract's examples.
        "start": b.start_at.astimezone(tz).isoformat(),
        "end": b.end_at.astimezone(tz).isoformat(),
        "status": b.status,
        "customFieldValues": b.attributes,
        "appliedConfig": {
            "flowConfigVersion": view.applied.version,
            "ruleSetVersion": view.applied.rule_set_version,
            **flow,
        },
        "history": history,
        "publicCode": b.public_code,
        "channel": b.channel,
        "payment": payment_summary(view.payment),
        "createdAt": b.created_at.isoformat(),
        "updatedAt": b.updated_at.isoformat(),
    }
