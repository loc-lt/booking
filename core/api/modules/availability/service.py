"""Public interface of the availability module: when is a resource open?

Opening hours are local times of the site's timezone, so a day is cut in local time and
converted to UTC instants. That keeps midnight and daylight-saving changes right.

Busy time (bookings) belongs to the booking module; callers pass it in. This module never
imports booking, so booking can call is_open() without a cycle.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Q, QuerySet

from kernel.errors import NotFound, ValidationFailed
from modules.availability.models import AvailabilityException, AvailabilityRule, ExceptionKind

Interval = tuple[datetime, datetime]


@dataclass(frozen=True, slots=True)
class ResourceRef:
    id: UUID
    location_id: UUID


@transaction.atomic
def set_weekly_hours(
    *,
    tenant_id: UUID,
    hours: dict[int, list[tuple[time, time]]],
    location_id: UUID | None = None,
    resource_id: UUID | None = None,
) -> None:
    """Replace the weekly hours of a site, or of one resource (which then ignores its site's
    hours). hours: weekday (0 = Monday) -> [(start, end)] in the site's local time."""
    if (location_id is None) == (resource_id is None):
        raise ValueError("Give exactly one of location_id, resource_id.")
    target = {"location_id": location_id} if location_id else {"resource_id": resource_id}
    errors = []
    for weekday, ranges in hours.items():
        ordered = sorted(ranges)
        for i, (start, end) in enumerate(ordered):
            if start >= end:
                errors.append(
                    {"field": f"weekly.{weekday}", "message": "opens must be before closes."}
                )
            if i and start < ordered[i - 1][1]:
                errors.append({"field": f"weekly.{weekday}", "message": "Ranges overlap."})
    if errors:
        raise ValidationFailed(errors)
    AvailabilityRule.objects.filter(**target).delete()
    AvailabilityRule.objects.bulk_create(
        [
            AvailabilityRule(
                tenant_id=tenant_id,
                weekday=weekday,
                start_local=start,
                end_local=end,
                **target,
            )
            for weekday, ranges in hours.items()
            for start, end in ranges
        ]
    )


def clear_resource_hours(*, resource_id: UUID) -> int:
    """The resource follows its site's hours again."""
    return AvailabilityRule.objects.filter(resource_id=resource_id).delete()[0]


def weekly_hours(
    *, location_id: UUID | None = None, resource_id: UUID | None = None
) -> list[tuple[int, time, time]]:
    target = {"location_id": location_id} if location_id else {"resource_id": resource_id}
    return [
        (r.weekday, r.start_local, r.end_local)
        for r in AvailabilityRule.objects.filter(**target).order_by("weekday", "start_local")
    ]


@transaction.atomic
def add_exception(
    *,
    tenant_id: UUID,
    kind: str,
    start: datetime,
    end: datetime,
    location_id: UUID | None = None,
    resource_id: UUID | None = None,
    reason_code: str | None = None,
    note: str | None = None,
    membership_id: UUID | None = None,
) -> AvailabilityException:
    """Block (holiday, maintenance) or open extra time, for a site or one resource. Bookings
    already made are not touched (API_KICH_BAN.md 4.3)."""
    if (location_id is None) == (resource_id is None):
        raise ValidationFailed.one("siteId", "Give exactly one of siteId, resourceId.")
    if end <= start:
        raise ValidationFailed.one("end", "Must be after start.")
    row = AvailabilityException.objects.create(
        tenant_id=tenant_id,
        location_id=location_id,
        resource_id=resource_id,
        kind=kind,
        during=(start, end),
        reason_code=reason_code,
        note=note,
        created_by_membership_id=membership_id,
    )
    row.refresh_from_db(fields=["during"])  # a range object, like rows read back later
    return row


def list_exceptions_qs(
    *,
    location_id: UUID | None = None,
    resource_id: UUID | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> QuerySet[AvailabilityException]:
    qs = AvailabilityException.objects.all()
    if location_id:
        qs = qs.filter(location_id=location_id)
    if resource_id:
        qs = qs.filter(resource_id=resource_id)
    if start or end:
        qs = qs.filter(during__overlap=(start, end))
    return qs


def get_exception(exception_id: UUID) -> AvailabilityException:
    row = AvailabilityException.objects.filter(id=exception_id).first()
    if row is None:
        raise NotFound("No availability exception with this id.")
    return row


@transaction.atomic
def delete_exception(exception_id: UUID) -> None:
    deleted, _ = AvailabilityException.objects.filter(id=exception_id).delete()
    if not deleted:
        raise NotFound("No availability exception with this id.")


def _merge(intervals: list[Interval]) -> list[Interval]:
    out: list[Interval] = []
    for start, end in sorted(intervals):
        if out and start <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def _subtract(base: list[Interval], cut: list[Interval]) -> list[Interval]:
    result = base
    for c_start, c_end in cut:
        nxt: list[Interval] = []
        for start, end in result:
            if c_end <= start or c_start >= end:
                nxt.append((start, end))
                continue
            if start < c_start:
                nxt.append((start, c_start))
            if c_end < end:
                nxt.append((c_end, end))
        result = nxt
    return result


def _local(day: date, at: time, tz: ZoneInfo) -> datetime:
    """A site-local wall-clock time as a UTC instant.

    Everything is compared in UTC: Python compares and subtracts two datetimes that share a
    tzinfo by wall clock, which is wrong across daylight-saving changes."""
    return datetime.combine(day, at, tzinfo=tz).astimezone(UTC)


def open_intervals(
    *, resources: list[ResourceRef], timezone_name: str, start: datetime, end: datetime
) -> dict[UUID, list[Interval]]:
    """Open time of each resource inside [start, end): weekly hours (resource rules replace
    site rules) + OPEN exceptions - BLOCK exceptions."""
    if not resources:
        return {}
    tz = ZoneInfo(timezone_name)
    resource_ids = [r.id for r in resources]
    location_ids = {r.location_id for r in resources}
    rules = list(
        AvailabilityRule.objects.filter(
            Q(resource_id__in=resource_ids) | Q(location_id__in=location_ids)
        )
    )
    by_resource: dict[UUID, list[AvailabilityRule]] = defaultdict(list)
    by_location: dict[UUID, list[AvailabilityRule]] = defaultdict(list)
    for rule in rules:
        if rule.resource_id:
            by_resource[rule.resource_id].append(rule)
        else:
            by_location[rule.location_id].append(rule)

    exceptions = list(
        AvailabilityException.objects.filter(
            Q(resource_id__in=resource_ids) | Q(location_id__in=location_ids),
            during__overlap=(start, end),
        )
    )

    first_day = start.astimezone(tz).date() - timedelta(days=1)
    last_day = end.astimezone(tz).date() + timedelta(days=1)
    days = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]

    result: dict[UUID, list[Interval]] = {}
    for res in resources:
        res_rules = by_resource.get(res.id) or by_location.get(res.location_id, [])
        opened: list[Interval] = []
        for day in days:
            for rule in res_rules:
                if rule.weekday != day.weekday():
                    continue
                if rule.valid_from and day < rule.valid_from:
                    continue
                if rule.valid_to and day > rule.valid_to:
                    continue
                opened.append((_local(day, rule.start_local, tz), _local(day, rule.end_local, tz)))
        mine = [
            e for e in exceptions if e.resource_id == res.id or e.location_id == res.location_id
        ]
        opened += [(e.during.lower, e.during.upper) for e in mine if e.kind == ExceptionKind.OPEN]
        blocked = [(e.during.lower, e.during.upper) for e in mine if e.kind == ExceptionKind.BLOCK]
        clipped = [(max(s, start), min(e, end)) for s, e in _merge(opened) if s < end and e > start]
        result[res.id] = _subtract(clipped, _merge(blocked))
    return result


def is_open(*, resource: ResourceRef, timezone_name: str, start: datetime, end: datetime) -> bool:
    """True if [start, end) lies entirely inside the resource's open time."""
    intervals = open_intervals(
        resources=[resource], timezone_name=timezone_name, start=start, end=end
    )[resource.id]
    return any(s <= start and end <= e for s, e in intervals)


def day_bounds(day: date, timezone_name: str) -> Interval:
    """[local midnight, next local midnight) of a site-local day, as UTC instants."""
    tz = ZoneInfo(timezone_name)
    return _local(day, time(0), tz), _local(day + timedelta(days=1), time(0), tz)


def free_slots(
    *,
    resources: list[ResourceRef],
    timezone_name: str,
    day: date,
    slot_minutes: int,
    busy: dict[UUID, list[Interval]],
    buffer_before: timedelta,
    buffer_after: timedelta,
) -> list[tuple[datetime, datetime, list[UUID]]]:
    """The day's slots in site-local time, each with the resources free for all of it.

    A slot is free for a resource when it is open for the whole slot and a booking of that
    slot (widened by the buffers) would not overlap any busy interval. Slots are listed even
    when nothing is free, so the screen can show them greyed out.
    """
    day_start, day_end = day_bounds(day, timezone_name)
    opened = open_intervals(
        resources=resources, timezone_name=timezone_name, start=day_start, end=day_end
    )
    step = timedelta(minutes=slot_minutes)
    tz = ZoneInfo(timezone_name)
    slots: list[tuple[datetime, datetime, list[UUID]]] = []
    # Slot boundaries are wall-clock times from local midnight (09:00, 09:30, ...).
    wall = datetime.combine(day, time(0))
    while wall < datetime.combine(day + timedelta(days=1), time(0)):
        slot_start = wall.replace(tzinfo=tz).astimezone(UTC)
        slot_end = (wall + step).replace(tzinfo=tz).astimezone(UTC)
        wall += step
        if slot_end <= slot_start:
            continue  # a wall-clock time skipped by a daylight-saving change
        open_for = [
            res
            for res in resources
            if any(s <= slot_start and slot_end <= e for s, e in opened[res.id])
        ]
        if not open_for:
            continue
        want_start, want_end = slot_start - buffer_before, slot_end + buffer_after
        free = [
            res.id
            for res in open_for
            if not any(b_s < want_end and want_start < b_e for b_s, b_e in busy.get(res.id, []))
        ]
        slots.append((slot_start.astimezone(tz), slot_end.astimezone(tz), free))
    return slots
