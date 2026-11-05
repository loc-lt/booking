import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-secret")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://booking_app:booking_app@localhost:55433/booking_core"
)
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-not-a-real-secret-32b")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("PAYMENT_WEBHOOK_SECRET", "test-only-webhook-secret")
os.environ.setdefault("API_DOCS_ENABLED", "true")
os.environ.setdefault("AUTH_RATE", "10000/min")
os.environ.setdefault("EMAIL_BACKEND", "django.core.mail.backends.locmem.EmailBackend")

from .base import *

DATABASES["default"]["CONN_MAX_AGE"] = 0
