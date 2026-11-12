# Booking core API (Django)

The backend of `contracts/openapi.yaml` (69 operations): API and worker, one image. The rules it
follows are in [docs/backend.md](../../docs/backend.md); how this code follows them, folder by
folder, is in the **backend handbook: [core/docs/](../docs/README.md)**.

> **Needs decision D-002 before merge.** `docs/backend.md` and `docs/architecture.md` still say
> Flask + SQLAlchemy + Alembic. This code is Django + DRF. All open points:
> [core/docs/open-decisions.md](../docs/open-decisions.md).

## Run it

From the repository root, with Docker Desktop running, Python 3.10+ and
[uv](https://docs.astral.sh/uv/) (`pip install uv`):

```bash
python scripts/dev.py up        # 1. postgres :55433, migrate, API :8000, worker; creates core/api/.env on first run
python scripts/dev.py seed      # 2. demo tenant: 2 sites, 3 resource types, 7 resources, rules, 5 people + one password
python scripts/dev.py docs      # 3. http://localhost:8000/api/docs: sign in, pick the tenant, try every endpoint
```

Configuration is one file, `core/api/.env`, copied from [`.env.example`](.env.example) (every
variable documented). Django reads it when you run `manage.py` or `pytest` directly; Compose
reads it through `scripts/dev.py`. Servers get their own.

Locally the code is mounted into the containers (`infra/compose.dev.yaml`): save a `.py` file
and the API and worker restart by themselves. Rebuild (`dev.py up`) only after a dependency
change.

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"<printed by seed>","password":"<printed by seed>"}'       # -> accessToken
curl -s http://localhost:8000/api/v1/me/tenants -H "Authorization: Bearer <token>"   # -> tenantId
curl -s http://localhost:8000/api/v1/resource-types -H "Authorization: Bearer <token>" -H "X-Tenant-Id: <tenantId>"
```

More: `python scripts/dev.py help` (logs, psql, timers, manage, down, reset);
[core/docs/getting-started.md](../docs/getting-started.md) for the virtualenv, the tests and
troubleshooting.

## Check it

```bash
python scripts/dev.py check     # what CI runs: ruff, ruff format, lint-imports, pytest (260 tests on real PostgreSQL)
```

Every tool runs through `uv run --locked`, which builds `core/api/.venv` from `uv.lock` on the
first run. Inside `core/api`: `uv sync`, `uv run pytest`, `uv run python manage.py …`.

The Postman scenario in the team's notes folder (`docs/postman/`, 198 requests covering all 69
operations) also checks every response against the contract's schema.

## Layout

```text
app/          settings (base, local, test, production; .env loader), urls, the local docs hub
kernel/       shared by every module, imports no module: auth, access (tenant + permissions),
              errors (RFC 9457), pagination, idempotency, jobs, history, db migration helpers
modules/      one Django app each; other modules may import only its service.py
  tenancy, users, identity, resources, config, availability, booking, payments, rules, events
worker/       run_worker: outbox delivery + due timers
tests/        everything CI runs
pyproject.toml  dependencies (pinned in uv.lock), ruff, pytest, import contracts
```

Each request: JWT → tenant + membership → view checks permission → request serializer →
**one** service function in one transaction (writes + transition_log + outbox) → response.
Details: [structure](../docs/structure.md), [request-lifecycle](../docs/request-lifecycle.md),
[engines](../docs/engines.md) (the thirteen guarantees and the test that proves each).

## Dependencies

Declared in `pyproject.toml` (`[project]` for runtime, `[dependency-groups] dev` for checks)
and pinned in `uv.lock`, which is committed: the image, CI and every laptop install the same
versions. Add one with `uv add`, after asking (root `CLAUDE.md`), and give it a row here.

| Package | Why | Alternative considered |
| --- | --- | --- |
| Django, djangorestframework | Web framework, request validation (team's Django experience) | Flask + Pydantic (the docs' original plan) |
| psycopg[binary] | PostgreSQL driver | — |
| PyJWT[crypto] | Token signing and verification (docs/backend.md) | — |
| jsonschema | Custom field and policy validation (docs/backend.md) | — |
| gunicorn | Serving (docs/backend.md) | — |
| pytest, pytest-django, ruff, import-linter | Tests and CI checks | — |

No camelCase library (serializers use the contract's names), no JSONLogic library (a small
evaluator in `modules/rules/jsonlogic.py`, tested against the shared example), no payment
SDK (the mock gateway is HMAC over the raw body, standard library only), no dotenv library
(`app/settings/__init__.py` reads `.env` with the standard library).
