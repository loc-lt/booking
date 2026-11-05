from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.urls import include, path

from app import docs


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness and database check, used by the deploy job and Compose."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


api_v1 = [
    path("", include("modules.identity.urls")),
    path("", include("modules.users.urls")),
    path("", include("modules.resources.urls")),
    path("", include("modules.availability.urls")),
    path("", include("modules.booking.urls")),
    path("", include("modules.payments.urls")),
    path("", include("modules.rules.urls")),
    path("", include("modules.events.urls")),
]

urlpatterns = [
    *docs.urlpatterns,
    path("api/healthz", healthz),
    path("api/v1/", include(api_v1)),
]
