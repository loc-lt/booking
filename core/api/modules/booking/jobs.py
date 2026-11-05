"""Booking timers, registered with the kernel's job runner. The worker calls them inside
tenant_scope(job.tenant_id); each one goes through transition() as SYSTEM."""

from kernel.jobs import register_job
from kernel.models import ScheduledJob
from modules.booking import lifecycle
from modules.booking.service import run_timer


def _handler(job: ScheduledJob) -> None:
    run_timer(booking_id=job.record_id, job_type=job.job_type)


for _job_type in (
    lifecycle.MARK_NO_SHOW,
    lifecycle.AUTO_COMPLETE,
    lifecycle.APPROVAL_TIMEOUT,
    lifecycle.EXPIRE_HOLD,
):
    register_job(_job_type)(_handler)
