"""Settings shared by every environment. All configuration comes from environment variables
(docs/operations.md, "Cloud-ready rules")."""

import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Missing environment variable {name}")
    return value


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


def database_from_url(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
        # One request = one transaction, so SET LOCAL app.tenant_id lives exactly as long
        # as the request (kernel/tenant_context.py).
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
    }


SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG", "false") == "true"
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,api")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.postgres",
    "rest_framework",
    "kernel",
    "modules.tenancy",
    "modules.users",
    "modules.identity",
    "modules.resources",
    "modules.config",
    "modules.availability",
    "modules.booking",
    "modules.payments",
    "modules.events",
    "modules.rules",
    "worker",
]

MIDDLEWARE = [
    "kernel.cors.LocalCorsMiddleware",
    "kernel.request_context.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

# Empty outside local development: Caddy serves apps and API on one address (kernel/cors.py).
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "")

ROOT_URLCONF = "app.urls"
WSGI_APPLICATION = "app.wsgi.application"
APPEND_SLASH = False

DATABASES = {"default": database_from_url(env("DATABASE_URL"))}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

REST_FRAMEWORK: dict[str, Any] = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["kernel.auth.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "kernel.errors.problem_handler",
    # Login, register, guest tokens: per client IP (identity views use scope "auth").
    "DEFAULT_THROTTLE_RATES": {"auth": env("AUTH_RATE", "30/min")},
    "UNAUTHENTICATED_USER": None,
    # ISO 8601 with offset, as the contract requires.
    "DATETIME_FORMAT": "iso-8601",
}

# Token verification (kernel/auth.py). Asymmetric keys from the auth service's JWKS are
# preferred; HS256 with a shared secret is the fallback (docs/backend.md, "Auth").
JWT = {
    "ISSUER": env("JWT_ISSUER", "https://auth.local"),
    "AUDIENCE": env("JWT_AUDIENCE", "booking-core"),
    "ALGORITHMS": env_list("JWT_ALGORITHMS", "HS256"),
    "JWKS_URL": env("JWT_JWKS_URL", ""),
    "SECRET": env("JWT_SECRET", ""),
    "LEEWAY_SECONDS": int(env("JWT_LEEWAY_SECONDS", "30")),
}

WORKER = {
    "POLL_SECONDS": float(env("WORKER_POLL_SECONDS", "1")),
    "BATCH_SIZE": int(env("WORKER_BATCH_SIZE", "100")),
    "MAX_ATTEMPTS": int(env("WORKER_MAX_ATTEMPTS", "10")),
}

# Sign-in (modules/identity, D-003). Access tokens are short; refresh tokens rotate.
AUTH = {
    "ACCESS_TTL_SECONDS": int(env("AUTH_ACCESS_TTL_SECONDS", "900")),
    "REFRESH_TTL_DAYS": int(env("AUTH_REFRESH_TTL_DAYS", "30")),
    "GUEST_TTL_SECONDS": int(env("AUTH_GUEST_TTL_SECONDS", "7200")),
    "RESET_TTL_SECONDS": int(env("AUTH_RESET_TTL_SECONDS", "3600")),
    "INVITATION_TTL_DAYS": int(env("AUTH_INVITATION_TTL_DAYS", "7")),
    "MAX_FAILED_LOGINS": int(env("AUTH_MAX_FAILED_LOGINS", "5")),
    "LOCK_MINUTES": int(env("AUTH_LOCK_MINUTES", "15")),
    # Where emailed links point: the member app's accept-invitation and reset-password pages.
    "APP_URL": env("AUTH_APP_URL", "http://localhost:5174"),
}
PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Invitation and password-reset emails. Local: printed by the console backend (container
# log). Servers: an SMTP backend via EMAIL_* variables (docs/operations.md).
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = int(env("EMAIL_PORT", "25"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", "false") == "true"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Booking Core <no-reply@localhost>")

# Payments (modules/payments). GATEWAY names new payment sessions; "mock" is the signed test
# gateway of local runs and the demo. Webhooks are verified with WEBHOOK_SECRET (HMAC-SHA256).
PAYMENTS = {
    "GATEWAY": env("PAYMENT_GATEWAY", "mock"),
    "WEBHOOK_GATEWAYS": env_list("PAYMENT_WEBHOOK_GATEWAYS", "mock"),
    "WEBHOOK_SECRET": env("PAYMENT_WEBHOOK_SECRET", ""),
}

# Browsable docs at /api/docs (app/docs.py): Swagger UI, ReDoc, the contract and the markdown
# docs of the repository. Local and demo only; production leaves it off.
API_DOCS = {
    "ENABLED": env("API_DOCS_ENABLED", "false") == "true",
    "REPO_DIR": env("API_DOCS_REPO_DIR", str(BASE_DIR.parent.parent)),
    "WORKSPACE_DIR": env("API_DOCS_WORKSPACE_DIR", ""),
}

LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"context": {"()": "kernel.request_context.ContextFilter"}},
    "formatters": {"json": {"()": "kernel.request_context.JsonFormatter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["context"],
            "formatter": "json",
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
