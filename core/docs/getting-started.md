# Getting started

Run the backend, sign in, run the tests. Ten minutes on a machine with Docker Desktop,
Python 3.10 or newer (for `scripts/dev.py`) and [uv](https://docs.astral.sh/uv/) (for the
checks; `pip install uv` is enough). Commands run from the repository root (the folder with
`infra/`, `core/` and `scripts/`) unless said otherwise.

## Three commands

```bash
python scripts/dev.py up      # 1. database :55433, migrations, API :8000, worker (first run: a few minutes)
python scripts/dev.py seed    # 2. a demo tenant: 2 sites, 3 resource types, 7 resources, 3 rules, 5 people
python scripts/dev.py docs    # 3. opens http://localhost:8000/api/docs
```

`seed` prints one password and the e-mail of each person (`demo-xxxxxx-owner@demo.test`,
`-staff`, `-lan`, `-tuan`, `-guest`). On the docs page, sign in with one of them, pick the
tenant, and every Swagger call carries the token and `X-Tenant-Id` for you.

What `up` started:

| Container | Role | Reach it |
| --- | --- | --- |
| `postgres` | PostgreSQL 17, role `booking_app` without `BYPASSRLS` | `localhost:55433`, or `python scripts/dev.py psql` |
| `migrate` | Runs `manage.py migrate` once, then exits | `python scripts/dev.py logs migrate` |
| `api` | Gunicorn, production settings, 2 workers, `--reload` | `http://localhost:8000/api/healthz` |
| `worker` | `manage.py run_worker --reload`: outbox delivery and due timers | `python scripts/dev.py logs worker` |

## Edit code, see it at once (hot reload)

`dev.py` starts the stack from two files: `infra/compose.yaml` (the stack CI also starts) and
`infra/compose.dev.yaml` (local only). The second mounts `core/api` over the image's copy of
the code and turns on reloading, so saving a `.py` file restarts the API's Gunicorn workers
and the worker process within about a second; `dev.py logs api` shows `Worker reloading:
… modified`. Rebuild with `dev.py up` only when `pyproject.toml` or `uv.lock` changes (new
package). A new migration: `python scripts/dev.py manage makemigrations <module>` writes it
into the checkout through the same mount, and `python scripts/dev.py manage migrate` applies
it.

The installed packages live in `/opt/venv` inside the image, outside the mount, so mounting
the source hides nothing. Started without the override (`docker compose -f
infra/compose.yaml up`), the containers run the code baked into the image, as a server does.

## Configuration: one `.env` file

`core/api/.env` holds every local setting. The first `dev.py up` copies it from
[`core/api/.env.example`](../api/.env.example), which documents each variable. Three readers
use the same file:

| Reader | How |
| --- | --- |
| Django on your machine (`manage.py`, `pytest`, `runserver`) | `app/settings/__init__.py` loads it before any settings module runs; variables already in your shell win |
| Docker Compose | `scripts/dev.py` passes `--env-file core/api/.env`; `infra/compose.yaml` reads it through `${VAR:-default}` |
| You | Edit it; `dev.py up` again |

Two values are fixed in `infra/compose.yaml` and not taken from the file: containers always run
`app.settings.production`, and their database host is `postgres:5432`. Without a `.env` the
Compose defaults apply, so `docker compose -f infra/compose.yaml up` alone (CI) still works.
The file is git-ignored; servers get their own (`docs/operations.md`, "Secrets").

## Sign in from a terminal

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo-xxxxxx-owner@demo.test","password":"<printed by seed>"}'
# -> accessToken (15 min), refreshToken (30 days, single use)

curl -s http://localhost:8000/api/v1/me/tenants -H "Authorization: Bearer <accessToken>"
# -> the tenants this person belongs to; take tenantId

curl -s http://localhost:8000/api/v1/resource-types \
  -H "Authorization: Bearer <accessToken>" -H "X-Tenant-Id: <tenantId>"
```

Every endpoint under `/api/v1` except `/auth/*`, `/me/tenants`, `/auth/password/change` and
the payment webhook needs both headers. The complete header rules are in
[request-lifecycle.md](request-lifecycle.md).

Other ways to get a token locally: `seed` also prints a 12-hour development token per person,
and `python scripts/dev.py token <sub> --email <email>` mints one (DEBUG only). Invitation and
password-reset e-mails are not sent; they appear in the worker and API logs, and
`python scripts/dev.py manage auth_link reset --email <email>` prints a fresh link.

## Run the checks that CI runs

Dependencies are declared in `core/api/pyproject.toml` and pinned in `core/api/uv.lock`
(committed). There is no separate virtualenv step: `check` runs every tool through
`uv run --locked`, which creates or updates `core/api/.venv` from the lock file first.
With the database container up:

```bash
python scripts/dev.py check     # ruff check, ruff format --check, lint-imports, pytest (260 tests, ~2 min)
python scripts/dev.py check -k lifecycle    # extra arguments go to pytest
```

Working inside `core/api` directly: `uv sync` (create or update `.venv`), `uv run pytest`,
`uv run python manage.py <command>`. Adding a package is `uv add <package>` (runtime) or
`uv add --dev <package>`, after asking (root `CLAUDE.md`: no new dependencies without asking),
then a row in `core/api/README.md` saying why.

Tests use `app.settings.test` and real PostgreSQL (`DATABASE_URL` from `.env`, default
`localhost:55433`); pytest-django creates and drops `test_booking_core`. They switch to a
non-superuser role when they find themselves superuser, so row-level security is really tested.

## Everything `dev.py` does

| Command | Does |
| --- | --- |
| `up` | Create `.env` if missing; `docker compose up -d --build` with the hot-reload override; wait for `/api/healthz` |
| `seed [--bare] [--slug x] [--tenant-id uuid] [--json]` | `manage.py seed_demo` inside the api container with local settings |
| `token <sub> [--email e]` | A development JWT (DEBUG only) |
| `manage <command> …` | Any management command inside the container: `create_tenant`, `add_member`, `auth_link`, `migrate`, `shell` |
| `timers <tenantId>` | Make the tenant's pending timers due now, so the worker runs them |
| `logs [api\|worker\|postgres\|migrate]` | Follow container logs |
| `psql` | SQL shell as `booking_app` (row-level security applies) |
| `check` | What CI runs, through `uv run --locked` |
| `docs` | Open the docs hub |
| `down` / `reset` | Stop; or stop, delete the database volume, and start again |

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `error during connect … dockerDesktopLinuxEngine` | Docker Desktop is not running. Start it and run `dev.py up` again |
| `pytest` fails with `connection timeout expired` | The database container is down: `docker compose -f infra/compose.yaml up -d postgres` |
| `401 UNAUTHENTICATED` on every call | Token expired (15 min) or signed with another `JWT_SECRET` than the API's. Sign in again; after editing `JWT_SECRET` in `.env`, `dev.py up` |
| `403 FORBIDDEN` | The person is not an active member of the tenant in `X-Tenant-Id`, or lacks the permission; `GET /me/tenants` lists their tenants |
| `422 VALIDATION_FAILED` with field `X-Tenant-Id` | The header is missing or not a UUID |
| Code change not visible | Started without `dev.py`? Only `infra/compose.dev.yaml` mounts the source; use `dev.py up`. A new package needs a rebuild: `dev.py up` again |
| Reload loops or a container exits after an edit | The edited file has a syntax or import error: `dev.py logs api` shows it; fix and save again |
| `uv is not on PATH` | `pip install uv`, then `dev.py check` again |
| Port 55433 or 8000 busy | Change `POSTGRES_HOST_PORT` in `.env` (and `DATABASE_URL` with it), or stop the other process |

## The scenario that proves the API

The team's notes folder next to this repository holds a Postman collection that calls all 69
operations in 198 requests and checks every response against the contract's schema:

```bash
python ../docs/postman/setup_env.py        # fresh tenants, tokens and links for one run
postman collection run ../docs/postman/booking-core-mvp.postman_collection.json \
  -e ../docs/postman/local.postman_environment.json
# expected: requests 198, failed 0; assertions 649, failed 0
```

[api-table-map.md](api-table-map.md) is generated from a traced run of that scenario.
