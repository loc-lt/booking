"""CORS for local development only.

On the demo server and in production, Caddy serves each app and forwards /api/* on the same
address, so there is no cross-origin call and CORS_ALLOWED_ORIGINS stays empty. Locally the
apps run on Vite (http://localhost:5173, 5174) and call the API on :8000.
"""

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

ALLOWED_HEADERS = "Authorization, Content-Type, X-Tenant-Id, Idempotency-Key, X-Request-ID"
ALLOWED_METHODS = "GET, POST, PATCH, OPTIONS"


class LocalCorsMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.origins = frozenset(settings.CORS_ALLOWED_ORIGINS)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        origin = request.headers.get("Origin")
        allowed = origin is not None and origin in self.origins
        if allowed and request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        if allowed:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
            response["Access-Control-Allow-Methods"] = ALLOWED_METHODS
            response["Access-Control-Expose-Headers"] = "X-Request-ID, Idempotent-Replayed"
            response["Vary"] = "Origin"
        return response
