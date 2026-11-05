"""Small helpers views share for query parameters."""

from datetime import datetime
from typing import Any
from uuid import UUID

from django.utils.dateparse import parse_datetime

from kernel.errors import ValidationFailed


def uuid_param(params: Any, name: str) -> UUID | None:
    raw = params.get(name)
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        raise ValidationFailed.one(name, "Must be a UUID.") from None


def datetime_param(params: Any, name: str) -> datetime | None:
    raw = params.get(name)
    if not raw:
        return None
    parsed = parse_datetime(raw.replace(" ", "+"))  # a bare + in a query string arrives as space
    if parsed is None or parsed.tzinfo is None:
        raise ValidationFailed.one(
            name, "Use ISO 8601 with an offset, e.g. 2026-12-15T09:00+07:00."
        )
    return parsed
