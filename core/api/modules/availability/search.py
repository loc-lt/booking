"""GET /availability: combines four modules, so it lives outside service.py (booking calls
availability.service, and this file calls booking.service: no import cycle)."""

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from kernel.errors import ValidationFailed
from modules.availability import service as availability
from modules.booking import service as booking
from modules.config import service as config
from modules.resources import service as resources


def search(
    *, site_id: UUID, resource_type_id: UUID, day: date, resource_id: UUID | None
) -> dict[str, Any]:
    location = resources.get_location(site_id)
    resource_type = resources.get_resource_type(resource_type_id)
    rows = resources.bookable_resources(location_id=location.id, resource_type_id=resource_type.id)
    if resource_id is not None:
        rows = [r for r in rows if r.id == resource_id]
        if not rows:
            raise ValidationFailed.one(
                "resourceId", "No bookable resource of this type at this site."
            )
    body = config.get_policy(resource_type.current_policy_version_id).body
    before = timedelta(seconds=body.get("buffer_before_seconds", 0))
    after = timedelta(seconds=body.get("buffer_after_seconds", 0))
    day_start, day_end = availability.day_bounds(day, location.timezone)
    refs = [availability.ResourceRef(id=r.id, location_id=r.location_id) for r in rows]
    busy = booking.busy_intervals(
        resource_ids=[r.id for r in rows], start=day_start - before, end=day_end + after
    )
    slot_minutes = resource_type.slot_minutes or 30
    slots = availability.free_slots(
        resources=refs,
        timezone_name=location.timezone,
        day=day,
        slot_minutes=slot_minutes,
        busy=busy,
        buffer_before=before,
        buffer_after=after,
    )
    return {
        "siteId": str(location.id),
        "resourceTypeId": str(resource_type.id),
        "date": day.isoformat(),
        "slotMinutes": slot_minutes,
        "slots": [
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "resourceIds": [str(rid) for rid in free],
            }
            for start, end, free in slots
        ],
    }
