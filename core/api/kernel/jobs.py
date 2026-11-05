"""Business timers on scheduled_jobs.

Modules schedule a job inside their own transaction and register one handler per job type.
The worker (worker/management/commands/run_worker.py) runs due jobs.
"""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from django.db.models import Q

from kernel.models import JobStatus, ScheduledJob

JobHandler = Callable[[ScheduledJob], None]
_handlers: dict[str, JobHandler] = {}


def register_job(job_type: str) -> Callable[[JobHandler], JobHandler]:
    def decorator(handler: JobHandler) -> JobHandler:
        _handlers[job_type] = handler
        return handler

    return decorator


def handler_for(job_type: str) -> JobHandler | None:
    return _handlers.get(job_type)


def schedule_job(
    *, tenant_id: UUID, job_type: str, object_code: str, record_id: UUID, run_at: datetime
) -> None:
    """Create or reschedule the one job of this type for this record (dedupe_key)."""
    dedupe_key = f"{job_type}:{record_id}"
    ScheduledJob.objects.update_or_create(
        dedupe_key=dedupe_key,
        defaults={
            "tenant_id": tenant_id,
            "job_type": job_type,
            "object_code": object_code,
            "record_id": record_id,
            "run_at": run_at,
            "status": JobStatus.PENDING,
            "attempts": 0,
            "locked_until": None,
            "last_error": None,
        },
    )


def cancel_jobs(*, object_code: str, record_id: UUID, job_types: list[str] | None = None) -> int:
    """Cancel pending jobs of a record, e.g. every timer of a cancelled booking."""
    qs = ScheduledJob.objects.filter(object_code=object_code, record_id=record_id).filter(
        Q(status=JobStatus.PENDING) | Q(status=JobStatus.RUNNING)
    )
    if job_types is not None:
        qs = qs.filter(job_type__in=job_types)
    return qs.update(status=JobStatus.CANCELLED)
