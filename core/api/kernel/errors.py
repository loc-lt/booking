"""Business errors and the handler that renders every error as problem details (RFC 9457)
with a stable `code` (docs/api.md, "Errors"). The frontend handles errors by `code`."""

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf
from rest_framework.response import Response

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"
TYPE_BASE = "https://errors.bookingcore.dev/"


class ApplicationError(Exception):
    code = "VALIDATION_FAILED"
    status = 422
    title = "Request failed"

    def __init__(self, detail: str | None = None, **extra: Any) -> None:
        super().__init__(detail or self.title)
        self.detail = detail
        self.extra = extra

    def body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": TYPE_BASE + self.code.lower().replace("_", "-"),
            "title": self.title,
            "status": self.status,
            "code": self.code,
        }
        if self.detail:
            body["detail"] = self.detail
        body.update(self.extra)
        return body


class ValidationFailed(ApplicationError):
    """422. `errors` is a list of {field, message}; field uses the contract's names."""

    code = "VALIDATION_FAILED"
    status = 422
    title = "Validation failed"

    def __init__(self, errors: list[dict[str, str]], detail: str | None = None) -> None:
        super().__init__(detail, errors=errors)

    @classmethod
    def one(cls, field: str, message: str) -> "ValidationFailed":
        return cls([{"field": field, "message": message}])


class BookingDenied(ApplicationError):
    """422. `reasons` is a list of {ruleId, message} from the evaluation trace."""

    code = "BOOKING_DENIED"
    status = 422
    title = "Booking not allowed"

    def __init__(self, reasons: list[dict[str, str]]) -> None:
        super().__init__(None, reasons=reasons)


class SlotTaken(ApplicationError):
    code = "SLOT_TAKEN"
    status = 409
    title = "Slot already taken"


class InvalidTransition(ApplicationError):
    code = "INVALID_TRANSITION"
    status = 409
    title = "Move not allowed"


class StaleVersion(ApplicationError):
    code = "STALE_VERSION"
    status = 409
    title = "Edit based on an outdated version"


class Unauthenticated(ApplicationError):
    code = "UNAUTHENTICATED"
    status = 401
    title = "Authentication required"


class Forbidden(ApplicationError):
    code = "FORBIDDEN"
    status = 403
    title = "Not allowed"


class NotFound(ApplicationError):
    code = "NOT_FOUND"
    status = 404
    title = "Not found"


def _drf_field_errors(detail: Any, prefix: str = "") -> list[dict[str, str]]:
    """Flatten DRF's nested error dict into [{field, message}] with dotted paths."""
    out: list[dict[str, str]] = []
    if isinstance(detail, dict):
        for key, value in detail.items():
            name = "" if key == "non_field_errors" else str(key)
            path = f"{prefix}.{name}" if prefix and name else (name or prefix)
            out.extend(_drf_field_errors(value, path))
    elif isinstance(detail, list):
        for index, item in enumerate(detail):
            if isinstance(item, dict | list):
                out.extend(_drf_field_errors(item, f"{prefix}[{index}]"))
            else:
                out.append({"field": prefix or "_", "message": str(item)})
    else:
        out.append({"field": prefix or "_", "message": str(detail)})
    return out


def _to_application_error(exc: Exception) -> ApplicationError | None:
    if isinstance(exc, ApplicationError):
        return exc
    if isinstance(exc, drf.ValidationError):
        return ValidationFailed(_drf_field_errors(exc.detail))
    if isinstance(exc, drf.ParseError | drf.UnsupportedMediaType):
        return ValidationFailed([{"field": "_", "message": str(exc.detail)}])
    if isinstance(exc, drf.NotAuthenticated | drf.AuthenticationFailed):
        return Unauthenticated(str(exc.detail))
    if isinstance(exc, drf.PermissionDenied | DjangoPermissionDenied):
        return Forbidden()
    if isinstance(exc, drf.NotFound | Http404):
        return NotFound()
    return None


def problem_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF EXCEPTION_HANDLER. Rolls back the request transaction on every error."""
    # Imported here: rest_framework.views loads the auth classes, which import this module.
    from rest_framework.views import set_rollback

    error = _to_application_error(exc)
    if error is None:
        if isinstance(exc, drf.APIException):
            # Framework errors outside the contract's list (405, 406, 429): keep the status.
            set_rollback()
            return Response(
                {
                    "type": "about:blank",
                    "title": str(exc.detail),
                    "status": exc.status_code,
                    "code": "VALIDATION_FAILED",
                },
                status=exc.status_code,
                content_type=PROBLEM_JSON,
            )
        return None  # unexpected: Django returns 500 and logs it
    set_rollback()
    headers = {"WWW-Authenticate": 'Bearer realm="api"'} if error.status == 401 else None
    return Response(error.body(), status=error.status, content_type=PROBLEM_JSON, headers=headers)
