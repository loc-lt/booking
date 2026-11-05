"""Status history for records other than bookings (resource, payment, refund, membership).

Bookings write their history in modules/booking/lifecycle.py. Everything else that changes
status calls record_status() in the same transaction, so transition_log covers
"vé, tiền, phòng" alike (docs/database/API_KICH_BAN.md 1).
"""

from uuid import UUID

from django.utils import timezone

from kernel.models import ActorKind, TransitionLog
from kernel.request_context import current_request_id


def record_status(
    *,
    tenant_id: UUID,
    object_code: str,
    record_id: UUID,
    action: str,
    from_status: str | None,
    to_status: str,
    membership_id: UUID | None = None,
    actor_kind: str | None = None,
    reason_code: str | None = None,
    note: str | None = None,
) -> TransitionLog:
    return TransitionLog.objects.create(
        tenant_id=tenant_id,
        object_code=object_code,
        record_id=record_id,
        action=action.upper(),
        from_status=from_status,
        to_status=to_status,
        actor_kind=actor_kind or (ActorKind.USER if membership_id else ActorKind.SYSTEM),
        actor_membership_id=membership_id,
        reason_code=reason_code,
        note=note,
        request_id=current_request_id(),
        at=timezone.now(),
    )


def history_of(object_code: str, record_id: UUID) -> list[TransitionLog]:
    return list(
        TransitionLog.objects.filter(object_code=object_code, record_id=record_id).order_by(
            "at", "id"
        )
    )
