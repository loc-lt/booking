"""Request id and JSON logs: every line carries the request id and tenant id
(docs/backend.md, "Logs")."""

import json
import logging
import re
from collections.abc import Callable
from contextvars import ContextVar

from django.http import HttpRequest, HttpResponse

from kernel.tenant_context import current_tenant_id, fresh_tenant_context
from kernel.uuid7 import uuid7

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def current_request_id() -> str | None:
    return request_id_var.get()


class RequestIdMiddleware:
    """Reuse X-Request-ID from Caddy or make one, and echo it in the response."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _VALID_ID.match(incoming) else str(uuid7())
        token = request_id_var.set(request_id)
        try:
            with fresh_tenant_context():
                response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response["X-Request-ID"] = request_id
        return response


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id()
        tenant = current_tenant_id()
        record.tenant_id = str(tenant) if tenant else None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "requestId": getattr(record, "request_id", None),
            "tenantId": getattr(record, "tenant_id", None),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)
