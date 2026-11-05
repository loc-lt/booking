from django.db import models
from django.utils import timezone

from kernel.uuid7 import uuid7


class Outbox(models.Model):
    """Events written in the same transaction as the change (docs/domain/events.md).

    No RLS: the worker reads across tenants and runs each subscriber inside the event's
    tenant. Never updated except for delivery bookkeeping; payload is never edited.
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField()
    event_type = models.TextField()
    event_version = models.IntegerField(default=1)
    aggregate_type = models.TextField()
    aggregate_id = models.UUIDField()
    payload = models.JSONField()
    request_id = models.TextField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    available_at = models.DateTimeField(default=timezone.now)
    attempts = models.IntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "outbox"
        indexes = [
            models.Index(
                fields=["available_at"],
                condition=models.Q(published_at__isnull=True),
                name="outbox_unpublished",
            ),
        ]


class ProcessedEvent(models.Model):
    """A subscriber handled this event. Lets every subscriber skip duplicates."""

    pk = models.CompositePrimaryKey("consumer", "event_id")
    consumer = models.TextField()
    event_id = models.UUIDField()
    processed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "processed_events"
