"""Base classes and the infrastructure tables every module shares.

transition_log: append-only history of every status move (booking, later resource, payment).
scheduled_jobs: business timers (no-show, auto-complete, approval timeout, hold expiry).
idempotency_keys: replaying a request with the same Idempotency-Key returns the first response.
"""

from django.db import models
from django.utils import timezone

from kernel.uuid7 import uuid7


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantModel(BaseModel):
    """Base for tenant-owned tables. Rows are isolated by the RLS policy from kernel.db.enable_rls.

    No single-column index on tenant_id: each table declares composite indexes that start
    with tenant_id, plus UNIQUE (tenant_id, id) as the target of same-tenant foreign keys.
    """

    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.PROTECT, related_name="+", db_index=False
    )

    class Meta:
        abstract = True


class ActorKind(models.TextChoices):
    USER = "USER"
    SYSTEM = "SYSTEM"
    GATEWAY = "GATEWAY"
    API_CLIENT = "API_CLIENT"


class TransitionLog(models.Model):
    """One row per status move. Insert only: never updated, never deleted."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.PROTECT, related_name="+", db_index=False
    )
    object_code = models.TextField()
    record_id = models.UUIDField()
    action = models.TextField()
    from_status = models.TextField(null=True, blank=True)
    to_status = models.TextField()
    actor_kind = models.TextField(choices=ActorKind.choices)
    actor_membership_id = models.UUIDField(null=True, blank=True)
    reason_code = models.TextField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    policy_version_id = models.UUIDField(null=True, blank=True)
    rule_versions = models.JSONField(default=list)
    request_id = models.TextField(null=True, blank=True)
    at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "transition_log"
        indexes = [
            models.Index(
                fields=["tenant", "object_code", "record_id", "at"], name="transition_log_record"
            ),
        ]


class JobStatus(models.TextChoices):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ScheduledJob(models.Model):
    """A business timer. No RLS: the worker scans every tenant for due jobs, then runs each
    one inside tenant_scope(job.tenant_id). Only code writes this table."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    tenant_id = models.UUIDField()
    job_type = models.TextField()
    object_code = models.TextField()
    record_id = models.UUIDField()
    run_at = models.DateTimeField()
    status = models.TextField(choices=JobStatus.choices, default=JobStatus.PENDING)
    attempts = models.IntegerField(default=0)
    dedupe_key = models.TextField(unique=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "scheduled_jobs"
        indexes = [
            models.Index(
                fields=["run_at"],
                condition=models.Q(status="PENDING"),
                name="scheduled_jobs_due",
            ),
            models.Index(
                fields=["tenant_id", "object_code", "record_id"], name="scheduled_jobs_record"
            ),
        ]


class IdempotencyKey(models.Model):
    pk = models.CompositePrimaryKey("tenant_id", "key")
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.PROTECT, related_name="+", db_index=False
    )
    key = models.TextField()
    membership_id = models.UUIDField(null=True, blank=True)
    endpoint = models.TextField()
    request_hash = models.BinaryField()
    status = models.TextField()  # IN_PROGRESS | COMPLETED
    response_code = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "idempotency_keys"
        indexes = [models.Index(fields=["expires_at"], name="idempotency_keys_expires")]
