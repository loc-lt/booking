"""Public interface of the events module: record events, deliver them to subscribers.

emit_event() runs in the caller's transaction: if the change is saved the event exists, if
the change is rolled back there is no event. The worker delivers later, at least once; each
subscriber records processed ids and skips repeats.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from kernel.request_context import current_request_id
from kernel.tenant_context import tenant_scope
from modules.events.models import Outbox, ProcessedEvent

logger = logging.getLogger(__name__)

SYSTEM = {"type": "system"}


def user_actor(membership_id: UUID) -> dict[str, str]:
    return {"type": "user", "id": str(membership_id)}


def emit_event(
    *,
    tenant_id: UUID,
    name: str,
    subject_type: str,
    subject_id: UUID,
    actor: dict[str, str],
    changes: dict[str, Any] | None = None,
    config_versions: dict[str, int] | None = None,
    data: dict[str, Any] | None = None,
) -> Outbox:
    """Record one event. Shape: docs/examples/event.json. Never call a gateway or send mail
    here; subscribers do that from the worker."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("emit_event() must run in the same transaction as the change.")
    row = Outbox(
        tenant_id=tenant_id,
        event_type=name,
        aggregate_type=subject_type,
        aggregate_id=subject_id,
        request_id=current_request_id(),
    )
    row.payload = {
        "id": str(row.id),
        "name": name,
        "version": 1,
        "tenantId": str(tenant_id),
        "subject": {"type": subject_type, "id": str(subject_id)},
        "actor": actor,
        "occurredAt": row.occurred_at.isoformat(),
        "changes": changes or {},
        "configVersions": config_versions or {},
        **({"data": data} if data else {}),
    }
    row.save(force_insert=True)
    return row


# ---------- subscribers ----------


@dataclass(frozen=True, slots=True)
class Subscriber:
    name: str  # stored in processed_events.consumer
    events: frozenset[str]  # event names, or {"*"} for every event
    handle: Callable[[dict[str, Any]], None]


_subscribers: list[Subscriber] = []


def subscribe(name: str, events: list[str]) -> Callable[[Callable[[dict[str, Any]], None]], Any]:
    """Register a subscriber. To react to something, subscribe to its event; never ask the
    booking module to call you (docs/domain/events.md, rule 4)."""

    def decorator(handle: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any]], None]:
        _subscribers.append(Subscriber(name=name, events=frozenset(events), handle=handle))
        return handle

    return decorator


def subscribers_for(event_type: str) -> list[Subscriber]:
    return [s for s in _subscribers if "*" in s.events or event_type in s.events]


def _deliver(event: Outbox) -> None:
    """Run every subscriber that hasn't processed this event yet, each in its own savepoint:
    one failing subscriber neither undoes nor blocks the others."""
    failures: list[str] = []
    for sub in subscribers_for(event.event_type):
        if ProcessedEvent.objects.filter(consumer=sub.name, event_id=event.id).exists():
            continue
        try:
            with tenant_scope(event.tenant_id):
                sub.handle(event.payload)
                ProcessedEvent.objects.create(consumer=sub.name, event_id=event.id)
        except Exception as exc:
            failures.append(f"{sub.name}: {exc!r}")
    if failures:
        raise RuntimeError("; ".join(failures))


def relay_batch(limit: int | None = None) -> int:
    """Deliver due events. FOR UPDATE SKIP LOCKED lets several workers run side by side.

    A failure retries with growing delays; after MAX_ATTEMPTS the event is parked (left
    unpublished, far in the future) and logged as an error for someone to look at.
    """
    cfg = settings.WORKER
    limit = limit or cfg["BATCH_SIZE"]
    now = timezone.now()
    with transaction.atomic():
        events = list(
            Outbox.objects.select_for_update(skip_locked=True)
            .filter(published_at__isnull=True, available_at__lte=now)
            .order_by("available_at", "id")[:limit]
        )
        for event in events:
            try:
                _deliver(event)
            except Exception as exc:
                event.attempts += 1
                event.last_error = repr(exc)[:2000]
                if event.attempts >= cfg["MAX_ATTEMPTS"]:
                    event.available_at = now + timedelta(days=365)
                    logger.error(
                        "outbox event %s parked after %s attempts", event.id, event.attempts
                    )
                else:
                    event.available_at = now + timedelta(seconds=min(2**event.attempts, 3600))
                    logger.warning("outbox event %s failed, retrying", event.id, exc_info=True)
            else:
                event.published_at = now
            event.save(update_fields=["attempts", "last_error", "available_at", "published_at"])
    return len(events)
