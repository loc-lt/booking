"""Cursor pagination: ?limit=50&cursor=... -> {"data": [...], "nextCursor": "..." | null}.

Ids are UUIDv7, so ordering by id DESC is "newest first" and the last id on a page is a
stable cursor (no OFFSET, no skipped or repeated rows when new rows arrive).
"""

import base64
from collections.abc import Callable
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from kernel.errors import ValidationFailed

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def _encode(value: UUID) -> str:
    return base64.urlsafe_b64encode(value.bytes).decode().rstrip("=")


def _decode(cursor: str) -> UUID:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        return UUID(bytes=base64.urlsafe_b64decode(padded))
    except (ValueError, TypeError):
        raise ValidationFailed.one("cursor", "Invalid cursor.") from None


def parse_limit(raw: str | None) -> int:
    if raw is None or raw == "":
        return DEFAULT_LIMIT
    try:
        limit = int(raw)
    except ValueError:
        raise ValidationFailed.one("limit", "Must be an integer.") from None
    if not 1 <= limit <= MAX_LIMIT:
        raise ValidationFailed.one("limit", f"Must be between 1 and {MAX_LIMIT}.")
    return limit


def paginate(
    queryset: QuerySet[Any],
    params: dict[str, str],
    serialize: Callable[[list[Any]], list[dict[str, Any]]],
) -> dict[str, Any]:
    limit = parse_limit(params.get("limit"))
    cursor = params.get("cursor")
    qs = queryset.order_by("-id")
    if cursor:
        qs = qs.filter(id__lt=_decode(cursor))
    rows = list(qs[: limit + 1])
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "data": serialize(rows),
        "nextCursor": _encode(rows[-1].id) if has_more and rows else None,
    }
