# One image for the API (default command) and the worker (`python manage.py run_worker`).
FROM python:3.12-slim

# uv installs the locked dependencies (pyproject.toml + uv.lock). Pinned like everything else.
COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /bin/uv

# The virtualenv lives outside /app so that infra/compose.dev.yaml can mount the source over
# /app (local hot reload) without hiding the installed packages.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=app.settings.production

WORKDIR /app
# Dependencies first, in their own layer: a code change does not reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev

COPY . .
RUN useradd --system --uid 10001 app
USER app

EXPOSE 8000
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
