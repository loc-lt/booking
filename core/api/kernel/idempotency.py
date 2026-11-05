"""Idempotency-Key (docs/api.md, "Retries").

The key row is written in the request transaction:
- First request: INSERT IN_PROGRESS, run the handler, save the response as COMPLETED.
- Same key while the first is still running: the INSERT waits on the primary key until the
  first commits, then replays its response. If the first failed, its row was rolled back
  and this request runs normally.
- Same key, different body: 422 VALIDATION_FAILED.
Error responses roll back the transaction, so they are not stored and a retry runs again.
"""

import hashlib
import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.response import Response

from kernel.errors import ValidationFailed
from kernel.models import IdempotencyKey

TTL = timedelta(hours=48)
HEADER = "Idempotency-Key"


def _hash(endpoint: str, body: Any) -> bytes:
    raw = json.dumps({"endpoint": endpoint, "body": body}, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).digest()


def run_idempotent(
    *,
    tenant_id: UUID,
    membership_id: UUID,
    key: str | None,
    endpoint: str,
    body: Any,
    handler: Callable[[], Response],
) -> Response:
    if not key:
        raise ValidationFailed.one(HEADER, "This header is required.")
    if len(key) > 255:
        raise ValidationFailed.one(HEADER, "At most 255 characters.")
    request_hash = _hash(endpoint, body)
    now = timezone.now()
    try:
        with transaction.atomic():  # savepoint: a duplicate must not break the request
            IdempotencyKey.objects.create(
                tenant_id=tenant_id,
                key=key,
                membership_id=membership_id,
                endpoint=endpoint,
                request_hash=request_hash,
                status="IN_PROGRESS",
                expires_at=now + TTL,
            )
    except IntegrityError:
        existing = IdempotencyKey.objects.select_for_update().get(tenant_id=tenant_id, key=key)
        if bytes(existing.request_hash) != request_hash or existing.membership_id != membership_id:
            raise ValidationFailed.one(
                HEADER, "This key was already used for a different request."
            ) from None
        if existing.status == "COMPLETED" and existing.expires_at > now:
            response = Response(existing.response_body, status=existing.response_code)
            response["Idempotent-Replayed"] = "true"
            return response
        # Expired: start over with this request.
        existing.status = "IN_PROGRESS"
        existing.expires_at = now + TTL
        existing.save(update_fields=["status", "expires_at"])

    response = handler()
    IdempotencyKey.objects.filter(tenant_id=tenant_id, key=key).update(
        status="COMPLETED", response_code=response.status_code, response_body=response.data
    )
    return response
