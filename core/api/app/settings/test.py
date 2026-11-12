"""Settings of pytest (pyproject.toml). Secrets and the database URL may come from the
developer's .env; everything that would change a test's outcome is forced below, after the
import, so a local .env (rate limits, e-mail backend, docs flag) cannot break the suite."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-secret")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://booking_app:booking_app@localhost:55433/booking_core"
)
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-not-a-real-secret-32b")
os.environ.setdefault("PAYMENT_WEBHOOK_SECRET", "test-only-webhook-secret")

from .base import *

DATABASES["default"]["CONN_MAX_AGE"] = 0
LOGGING["root"]["level"] = "WARNING"
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {"auth": "10000/min"}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
API_DOCS["ENABLED"] = True
