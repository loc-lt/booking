"""The worker: delivers outbox events and runs due timers. Same image as the API, different
command (`python manage.py run_worker`). Several workers can run side by side: both loops
claim rows with FOR UPDATE SKIP LOCKED."""

import logging
import signal
import time
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from kernel.jobs import handler_for
from kernel.models import JobStatus, ScheduledJob
from kernel.tenant_context import tenant_scope
from modules.events.service import relay_batch

logger = logging.getLogger(__name__)

LOCK_FOR = timedelta(minutes=5)


def _claimable(now: datetime) -> Q:
    """Pending jobs, and running jobs whose worker died (lock expired)."""
    return Q(status=JobStatus.PENDING) | Q(status=JobStatus.RUNNING, locked_until__lt=now)


def run_due_jobs(limit: int = 100) -> int:
    """Claim due jobs, then run each in its own transaction as its tenant.

    Claiming sets RUNNING and locked_until, so a crashed worker's jobs are picked up again
    once the lock expires. A failed job retries with growing delays, then is marked FAILED.
    """
    now = timezone.now()
    with transaction.atomic():
        jobs = list(
            ScheduledJob.objects.select_for_update(skip_locked=True)
            .filter(_claimable(now), run_at__lte=now)
            .order_by("run_at")[:limit]
        )
        for job in jobs:
            job.status = JobStatus.RUNNING
            job.locked_until = now + LOCK_FOR
            job.attempts += 1
            job.save(update_fields=["status", "locked_until", "attempts"])

    max_attempts = settings.WORKER["MAX_ATTEMPTS"]
    for job in jobs:
        handler = handler_for(job.job_type)
        try:
            if handler is None:
                raise LookupError(f"No handler for job type {job.job_type}")
            with tenant_scope(job.tenant_id):
                handler(job)
        except Exception as exc:
            failed = job.attempts >= max_attempts
            ScheduledJob.objects.filter(id=job.id).update(
                status=JobStatus.FAILED if failed else JobStatus.PENDING,
                run_at=timezone.now() + timedelta(seconds=min(2**job.attempts * 5, 3600)),
                locked_until=None,
                last_error=repr(exc)[:2000],
            )
            logger.exception("job %s %s failed", job.job_type, job.id)
        else:
            ScheduledJob.objects.filter(id=job.id).update(status=JobStatus.DONE, locked_until=None)
    return len(jobs)


class Command(BaseCommand):
    help = "Deliver outbox events and run due scheduled jobs."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--once", action="store_true", help="Run one pass and exit.")

    def handle(self, *args: Any, **options: Any) -> None:
        stopping = False

        def stop(*_: Any) -> None:
            nonlocal stopping
            stopping = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        poll = settings.WORKER["POLL_SECONDS"]
        logger.info("worker started")
        while not stopping:
            events = relay_batch()
            jobs = run_due_jobs()
            if options["once"]:
                break
            if not events and not jobs:
                time.sleep(poll)
        logger.info("worker stopped")
