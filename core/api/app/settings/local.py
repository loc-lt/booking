import os
from pathlib import Path

os.environ.setdefault("DJANGO_SECRET_KEY", "local-only-not-secret")
os.environ.setdefault("DJANGO_DEBUG", "true")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://booking_app:booking_app@localhost:55433/booking_core"
)
# Local tokens are minted with `python manage.py dev_token`. Never use this secret elsewhere.
os.environ.setdefault("JWT_SECRET", "local-only-jwt-secret-change-me-32bytes")

# Vite dev servers of the member and console apps.
os.environ.setdefault(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174",
)
os.environ.setdefault("PAYMENT_WEBHOOK_SECRET", "local-only-webhook-secret")
os.environ.setdefault("API_DOCS_ENABLED", "true")
# Team notes next to the repository (c:/workspace/.../booking/docs), when that folder exists.
# Inside the container the file sits at /app/app/settings/, with no such parent: skip.
_parents = Path(__file__).resolve().parents
_workspace_docs = _parents[5] / "docs" if len(_parents) > 5 else None
if _workspace_docs and _workspace_docs.is_dir():
    os.environ.setdefault("API_DOCS_WORKSPACE_DIR", str(_workspace_docs))

from .base import *
