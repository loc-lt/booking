# Building the backend from an empty folder

This page follows the backend from the day `core/core/` held a single `CLAUDE.md` to the code
that runs today. Each phase says which folders and files were created, **why each was needed
at that point, why it carries its name, and what every file in it does**. It starts from
[build-history.md](build-history.md) (the short version: phases, order, plan vs result) and
adds the folder-by-folder detail. [structure.md](structure.md) is the lookup table for the
finished tree; this page is the story of how that tree grew.

Read it once from top to bottom, then come back to a phase when you work in its folder.

> **How this was reconstructed.** The code reached git in one commit (`af59fc3 fix: backend
> core APIs`, 2026-11-05) plus uncommitted work after it, so git history does not show the
> order. The order below comes from the team's plan (`KE_HOACH_CODE_BE.md`, notes folder) and
> the work log. Files are placed in the phase where they first became necessary; some grew in
> later phases, and that is said where it matters.

## The starting point (2026-11-02)

What existed in the repository before the first backend file:

| Path | Since | What it meant for the backend |
| --- | --- | --- |
| `core/CLAUDE.md` | 2026-10-22 | Loads `docs/backend.md` for anyone working in `core/`: the rules came before the code. |
| `docs/` (`backend.md`, `architecture.md`, `domain/*`, `api.md`, `operations.md`, `decisions.md`) | 2026-10-22 | The specification: modules, `service.py`, `transition()`, outbox, row-level security, the exclusion constraint, the worker. |
| `contracts/openapi.yaml` | 2026-10-22 | 16 operations; the frontend owned its shape and had worked against generated mocks for two weeks. |
| `.gitlab-ci.yml` | 2026-10-22 | Already expected a Python dependency file in `core/api/`, `ruff`, `lint-imports`, `pytest core/api/tests` and `docker build core/api`. The folder name `core/api` was therefore fixed before any code. |
| `infra/Caddyfile`, `infra/web/` | 2026-10-22 | The demo server's router and the frontend image. No backend container yet. |
| `scripts/merge-docs.py` | 2026-10-22 | Builds the root `README.md` from `docs/`. `scripts/` was the place for repository tools. |
| The team's database design (24 tables, DBML, notes folder) | October | The tables; it disagreed with `docs/backend.md` on several names. |

## Phase 0: decisions before code

Two sources disagreed before a line was written: `docs/backend.md` described Flask,
SQLAlchemy, Alembic and a table set (`field_defs`, `config_versions`, `booking_events`), while
the team's database design had 24 tables and the team's experience was Django
(`paihong_apis`). The choice was Django + DRF with the 24-table design, recorded as proposed
decision **D-002** and a list of open items ([open-decisions.md](open-decisions.md)). Also
settled here: the database stores the contract's nine booking statuses rather than the seven
of the DBML, which makes `transition()` a direct copy of the table in
`docs/domain/booking.md`.

What was reused from an earlier Django prototype (`backend/rise`, since deleted): the UUIDv7
helper, `BaseModel`/`TenantModel`, the migration helpers for RLS and same-tenant keys, the
tenant context, the custom-field compiler idea, and the outbox relay. Each moved into
`kernel/` or `modules/config/` with imports fixed; nothing else was copied.

No file was created in this phase. Its output is the reason for half the names below.

## Phase 1: the skeleton (03/11)

Goal: a container that starts, connects to PostgreSQL as a role that row-level security
applies to, answers `GET /api/healthz`, and passes ruff. Nothing about bookings yet.

### `core/api/`: the project folder

**Why it exists:** one deployable unit for the API and the worker (`docs/architecture.md`,
`docs/operations.md`: "the worker runs from the same image").
**Why the name:** `docs/architecture.md` and `.gitlab-ci.yml` already used `core/api`.

Files created at its top, in this order:

| File | Why it was needed first | What it does |
| --- | --- | --- |
| `pyproject.toml` | The checks had to exist before the code they check | ruff rules (line length 100, security and Django rules on), pytest settings (`DJANGO_SETTINGS_MODULE = app.settings.test`), and the **two import-linter contracts**: modules use each other only through `service.py`; the kernel imports no module. The contracts came first so the module boundary existed before any module did. Since Phase 11 it also declares the dependencies. |
| `requirements.txt`, `requirements-dev.txt` | CI installed from a requirements file | Runtime and dev packages with version ranges. **Replaced in Phase 11** by `pyproject.toml` + `uv.lock`. |
| `manage.py` | Django's command entry point | Sets `DJANGO_SETTINGS_MODULE` to `app.settings.local` when nothing else says otherwise, so `python manage.py …` on a laptop works with no setup. |
| `Dockerfile` | CI's `build_images` job builds `core/api` | `python:3.12-slim`, dependencies in their own layer, a non-root user (`app`, uid 10001), Gunicorn as the default command. The worker uses the same image with another command. |
| `.dockerignore` | Keep the image small and free of secrets | Excludes `.venv`, caches, `tests` and `.env`. |
| `README.md` | Somebody opens the folder | The short entry page: three commands, the layout, the dependency table with a reason per package. |

### `core/api/app/`: the Django project package

**Why it exists:** Django needs one "project" package for settings, the URL root and the
WSGI entry.
**Why the name:** the same role and name as `paihong_apis/app/`, which the team knows. It
holds no business code, so a neutral name fits.

| File | What it does |
| --- | --- |
| `__init__.py` | Empty package marker. |
| `settings/` (a package, not one file) | Four environments need different defaults without `if` branches: one file each, all starting from `base`. |
| `settings/base.py` | Everything shared. `env()`, `env_bool()`, `env_list()` read the environment; `database_from_url()` turns `DATABASE_URL` into Django's dict with `ATOMIC_REQUESTS=True`, so one request is one transaction and `SET LOCAL app.tenant_id` lives exactly as long as the request. `INSTALLED_APPS`, the middleware list, DRF pointed at **our** authentication class and exception handler before either existed (so the names were fixed early), `USE_TZ=True`, `TIME_ZONE="UTC"`, JSON logging. |
| `settings/local.py` | Defaults for a laptop when a variable is missing (DEBUG on, the database on `localhost:55433`, a local JWT secret, the Vite origins), then `from .base import *`. |
| `settings/test.py` | What pytest uses. Since Phase 10 it **forces** the values that change test results (no throttling, in-memory e-mail, docs on), so a developer's `.env` cannot break the suite. |
| `settings/production.py` | `DEBUG=False`, `USE_X_FORWARDED_HOST` for Caddy. Every other value must come from the environment. |
| `urls.py` | `GET /api/healthz` running `SELECT 1` (Compose and the deploy job check it), and `/api/v1/` including each module's `urls.py`. In this phase only the health check existed. |
| `wsgi.py` | The object Gunicorn serves. |

### Outside `core/api/`: running it

| Path | Why | What it does |
| --- | --- | --- |
| `infra/compose.yaml` | `docs/operations.md`: locally the API, worker and database run in Compose | Four services: `postgres` (17), `migrate` (runs `manage.py migrate` once, then exits), `api`, `worker`. `api` and `worker` start only after `migrate` succeeded: migrations are a separate step, never at app start (`docs/backend.md`). |
| `infra/postgres/init.sql` | Row-level security does not apply to superusers or table owners with `BYPASSRLS` | Runs once when the volume is created: creates `booking_app` (login, not superuser, `NOBYPASSRLS`) and the `booking_core` database. Everything the API does goes through this role. |
| `scripts/dev.py` | The team works on Windows; `make` and shell scripts are not a given | One Python file, standard library only: `up`, `down`, `reset`, `logs`, `psql`, `check`, later `seed`, `token`, `timers`, `manage`, `docs`. Placed in `scripts/` next to `merge-docs.py`. |

**Done when** Compose came up, `/api/healthz` answered 200, and ruff was clean.

## Phase 2: the kernel, tenants and people (04–05/11)

Every later endpoint needs a verified token, a tenant and a permission check, so this came
before any business table.

### `core/api/kernel/`: what every module stands on

**Why it exists:** tenancy, auth, errors, pagination and migration helpers are needed by all
ten modules and must not belong to any one of them.
**Why the name:** not `core` (the repository is `core/` and the docs say "the core" for the
whole product), not `common` or `utils` (a kernel is a layer with a rule: it imports no
module; a drawer has no rule). import-linter's second contract enforces it.
**Why it is a Django app** (`apps.py`, `migrations/`): it owns three tables (below).

Created in this order:

| File | What it does, and why at this point |
| --- | --- |
| `uuid7.py` | `uuid7()`: time-ordered ids (`docs/backend.md`: "IDs are UUIDv7"). Every table needs it, so it came first. Reused from the prototype. |
| `models.py` | `BaseModel` (UUIDv7 `id`, `created_at`, `updated_at`) and `TenantModel` (adds `tenant`). Every model of every module inherits one of them. In Phase 5 it gained the three infrastructure tables. |
| `db.py` | Helpers that return `RunSQL` operations for migrations: `enable_rls(table)` (enable and **force** row-level security, policy on `current_setting('app.tenant_id')`), `same_tenant_fk()` (a composite foreign key `(tenant_id, x_id)`, so a row can never point into another tenant), `attributes_check()`. Plus `violated_constraint()` and `sqlstate()` to read a database error. |
| `tenant_context.py` | The tenant of the current request or job in a `ContextVar`. `activate_tenant()` runs `SET LOCAL app.tenant_id`; `activate_user()` sets `app.user_id`; `tenant_scope()` is the context manager the worker uses per job; `fresh_tenant_context()` resets it per request. |
| `errors.py` | `ApplicationError` and one subclass per contract error code (`ValidationFailed`, `NotFound`, `Forbidden`, `Unauthenticated`, later `BookingDenied`, `SlotTaken`, `InvalidTransition`, `StaleVersion`). `problem_handler()` turns any exception, DRF's own included, into RFC 9457 `application/problem+json` with a stable `code`, from day one. |
| `pagination.py` | Cursor pagination (`?limit=&cursor=` → `{data, nextCursor}`), no OFFSET, as the contract requires. |
| `params.py` | `uuid_param()`, `datetime_param()`: query parameters that fail with the field's name. |
| `serializers.py` | `AwareDateTimeField`: a timestamp without an offset is rejected. |
| `request_context.py` | `RequestIdMiddleware` (reuses `X-Request-ID` or makes one, echoes it) and the JSON log formatter that puts request id and tenant id on every line (`docs/backend.md`, "Logs"). |
| `cors.py` | `LocalCorsMiddleware`: the frontend apps ran on Vite (`:5173`, `:5174`) and needed the real API on `:8000`. Empty on servers, where Caddy serves apps and API on one address. |
| `auth.py` | `AuthAdapter.verify()` (signature, `exp`, `iss`, `aud`; JWKS or HS256) and `JWTAuthentication`, DRF's authentication class. It maps `sub` to a core user through `modules.users.service.user_from_claims`, resolved **by import path string**, so the kernel still imports no module. |
| `access.py` | `TenantAPIView`, the base class of every tenant endpoint: reads `X-Tenant-Id`, activates the tenant, loads the caller's active membership and permission grants into `request.access`, or answers 403. `require_perm()`, `require_somewhere()`, `require_any()` are what views call. |
| `permissions.py` | The permission codes (`booking.create`, `payment.refund`, …; 27 today) and their descriptions, served by `GET /permissions`. |
| `devtokens.py` | `mint()`: development tokens (DEBUG only), so the frontend could call the real API before sign-in existed. Since Phase 9 also `sign()`, used by `modules/identity` to issue real tokens. |
| `management/commands/dev_token.py` | `manage.py dev_token --sub x --email y`. `management/commands/` is Django's fixed location for custom commands. |
| `apps.py` | The `AppConfig` that makes `kernel` an installed app. |
| `migrations/` | `0001_initial.py` (generated) and `0002_db_rules.py` (hand-written RLS), for the tables added in Phase 5. |

### `core/api/modules/`: one folder per bounded context

**Why it exists:** `docs/backend.md` and `docs/architecture.md` list the core's modules; each
owns its tables.
**Why the name:** the docs call them modules. Each is a Django app with its own `models.py`
and `migrations/`, so "a module owns its data" is literal: a model class lives in exactly one
app (unlike `paihong_apis/core/models.py`, where every model lives together).
`modules/__init__.py` is an empty package marker.

**The shape every module follows** (fixed here, with the first two modules):

| File | Holds | Rule |
| --- | --- | --- |
| `apps.py` | `AppConfig` | `ready()` imports whatever must register (jobs, event subscribers). |
| `models.py` | The module's tables | Private: no other module imports it. |
| `service.py` | The public interface | The **only** file another module may import (import-linter). One function = one transaction's worth of work. |
| `views.py` | One class per path | Permission check → serializer → **one** service call → response. No business logic. |
| `urls.py` | The paths | kebab-case, no trailing slash, as in the contract. |
| `serializers.py` | Request validation and response shaping | Only where bodies are large; small ones sit in `views.py`. |
| `migrations/` | `0001_initial.py` (generated), `000N_db_rules.py` (hand-written SQL) | Hand-written SQL kept in its own file so reviewers find RLS, keys and constraints in one place. |
| `management/commands/` | Commands for operators | Django's fixed location. |

#### `modules/tenancy/`

**Why first:** every other table points at `tenants`.
**Why the name:** `docs/architecture.md`'s module name; "tenant" is the glossary term for a
customer organisation.

| File | What it does |
| --- | --- |
| `models.py` | `Tenant` (slug, name, status, default timezone, locale and currency, `settings` JSON). No `tenant_id` and no row-level security: it *is* the tenant. |
| `service.py` | `create_tenant()`, `get_tenant()`, `tenant_currency()`. |
| `management/commands/create_tenant.py`, `add_member.py` | Platform commands: a new tenant with its system roles; a person into a tenant. There is no public "create tenant" endpoint, by design. |
| `migrations/0001_initial.py` | The `tenants` table. |

#### `modules/users/`

**Why now:** a token's `sub` must map to a person, and a person must be a member of the
tenant with roles before any permission check can pass.
**Why the name:** the module list's `users`; it holds people *and* their memberships, roles
and grants, because all of them answer "who may do what here".

| File | What it does |
| --- | --- |
| `models.py` | `User`, `Membership` (person × tenant, with status), `Role`, `RolePermission`, `MembershipRole` (role, optionally limited to one site). Five tables; `users` has no `tenant_id` and no row-level security (one person, many tenants), the other four do. |
| `constants.py` | The five system roles (`owner`, `admin`, `staff`, `member`, `guest`) and their permission sets. Kept in code, not in `role_permissions`, so a new permission reaches every tenant with the next deploy. |
| `service.py` | `user_from_claims()` (the kernel's auth calls it), `resolve_access()` (what `TenantAPIView` loads), memberships, roles, grants, invitations, member status. The largest public interface after booking. |
| `views.py`, `urls.py` | `/me`, `/permissions`, `/roles`, `/members` and their actions. |
| `migrations/0001_initial.py`, `0002_db_rules.py` | `0001` creates the five tables; `0002_db_rules.py` adds RLS and the composite same-tenant keys, and runs after the first migrations of `resources` and `config` because some keys point into their tables. The links to `locations` (a member's default site, a role limited to one site) were added once `locations` existed in Phase 3; the migration files in the repository are in their final shape, not one file per phase. `0003_own_memberships.py` came in Phase 9. |

### `core/api/tests/`: one folder for every test

**Why it exists now:** `docs/backend.md`: tests ship with the code.
**Why at the top and not per module:** almost every test goes through HTTP and touches several
modules (a booking needs a tenant, a person, a site, a type and a resource). One `conftest.py`
that builds that world serves all of them.

| File | What it does |
| --- | --- |
| `conftest.py` | `build_world()` / the `world` and `world_b` fixtures (two tenants with roles, a site, people, tokens); `client_for()` sets both headers; `make_token()`. `django_db_setup` switches to a non-superuser role when the test database was created by a superuser (CI), so row-level security is really exercised. Later phases added `create_type()`, `create_resource()`, `book()`, `freeze()`. |
| `test_auth_and_tenancy.py` | Expired, wrongly signed and wrong-audience tokens → 401; a non-member → 403; tenant A cannot read tenant B. |

## Phase 3: sites, resource types, policies, fields, resources (05–06/11)

The console already had screens for resource types, so the first business endpoints were
theirs. Two modules were built together, because the contract's `ResourceType` is assembled
from three tables in two modules.

#### `modules/resources/`

**Why the name:** the glossary's "resource" (anything bookable) and the module list.

| File | What it does |
| --- | --- |
| `models.py` | `Location` (a site: IANA timezone, address, coordinates; "site" in the API, `locations` in the database design), `ResourceType` (code, booking mode, slot length or full day, current policy version), `Resource` (site, type, capacity, status, custom field values in `attributes` JSONB). |
| `service.py` | Sites, types and resources: create, update, status moves (`move_resource`), `bookable_resources()`, `ResourceTypeView` (a type with its current policy and fields, assembled from `config`). Every write locks the row it changes (`select_for_update`). |
| `serializers.py` | The contract's request bodies, including the nested `flowConfig` (check-in, cancellation, limits, buffers, payment), and `resource_type_json()`, `resource_json()`, `site_json()`. The largest serializer file, because `flowConfig` is the core's main configuration surface. |
| `views.py`, `urls.py` | `/sites`, `/resource-types` (versions, restore, fields, archive), `/resources` (maintenance, activate, deactivate). |
| `migrations/0001_initial.py`, `0002_db_rules.py` | Tables and the GIN index on `attributes` (`0001`); RLS, same-tenant keys and checks (`0002`). |

Sites (`POST /sites`, opening hours) were added to the contract here: the design needed them
and no screen had asked yet.

#### `modules/config/`

**Why separate from `resources`:** versioned configuration (`docs/domain/configuration.md`) is
its own concern: immutable versions, `baseVersion` checks, history and restore. Resources
*use* a policy version; `config` owns how versions are made.
**Why the name:** the module list's `config`.

| File | What it does |
| --- | --- |
| `models.py` | `PolicyVersion` (immutable policy bodies), `FieldDefinition` (custom fields, with status for archiving), `CustomObject`, `ObjectSchemaVersion` (the compiled form per version). |
| `policy.py` | The JSON Schema of a policy body and the **two-way map** between the contract's `flowConfig` (minutes) and the stored body (seconds). Added the `cancellation.allowedUntilMinutesBefore` key the design lacked. |
| `fields.py` | `check_definitions()`, `compile_schema()` (definitions → JSON Schema, using `pattern` instead of `format` so Ajv in the browser and `jsonschema` on the server agree), `check_values()`. Reused idea from the prototype. |
| `service.py` | `publish_policy()` (`STALE_VERSION` on a wrong `baseVersion`; a no-op edit publishes nothing), version list and restore, `add_fields()`, `archive_field()`, `validate_values()`. |
| `migrations/0001_initial.py`, `0002_initial.py`, `0003_db_rules.py` | Django generated two "initial" migrations because of foreign keys into `resources` (it splits a cycle that way); then the hand-written rules. |

No `views.py`: `config` is reached through `resources`' endpoints.

Tests: `test_resource_types.py`, `test_config_flex.py`, `test_sites_and_resources.py`.

## Phase 4: availability (09–10/11, done early)

**Why the name:** the module list's `availability`; it answers one question, "when is this
resource open, and which slots are free?"

| File | What it does |
| --- | --- |
| `models.py` | `AvailabilityRule` (weekly hours in **local wall-clock time** with the site's timezone), `AvailabilityException` (closures and extra openings, `ExceptionKind`). |
| `service.py` | `set_weekly_hours()`, exceptions, and the time maths: `open_intervals()` cuts each day in local time, converts to UTC, subtracts exceptions and adds buffers; `free_slots()` cuts to the type's slot length; `is_open()`. Daylight saving and midnight stay right because days are cut locally. |
| `search.py` | The free-slot search across resources. It needs resources, availability and bookings at once, so it sits outside `service.py` with imports pointing one way, to avoid a cycle with `booking`. |
| `views.py`, `urls.py` | `/availability`, `/sites/{id}/hours`, `/resources/{id}/hours`, `/availability-exceptions`. |
| `migrations/0001_initial.py`, `0002_initial.py`, `0003_db_rules.py` | As in `config`. |

Tests: `test_availability.py` (local time vs UTC, DST, buffers).

## Phase 5: the pipeline, `transition()`, no double booking

The part the demo cannot lose, built in this order.

### Kernel additions

| File | What was added |
| --- | --- |
| `kernel/models.py` | `TransitionLog` (one insert-only row per status move of any object), `ScheduledJob` (timers: type, record, `run_at`, status, attempts, lock), `IdempotencyKey`. They are kernel tables because more than one module writes them. |
| `kernel/idempotency.py` | `run_idempotent()`: stores the `Idempotency-Key` with a hash of endpoint and body; a replay returns the first response, the same key with another body is a 422. Required on `POST /bookings`. |
| `kernel/jobs.py` | `register_job(type, handler)`, `schedule_job()`, `cancel_jobs()`: modules schedule timers inside their own transaction; the worker (Phase 6) runs them. |

### `modules/events/`

**Why before booking:** `transition()` must write its event in the same transaction, so the
outbox had to exist first (`docs/domain/events.md`).
**Why the name:** the module list's `events`.

| File | What it does |
| --- | --- |
| `models.py` | `Outbox` (events waiting for delivery; a partial index on undelivered rows) and `ProcessedEvent` (which subscriber handled which event, so a repeat is skipped). |
| `service.py` | `emit_event()` (runs in the caller's transaction: no commit, no event), `subscribe()`, `relay_batch()` (claims undelivered rows with `FOR UPDATE SKIP LOCKED`, hands each to its subscribers, retries with growing delays). Reused from the prototype's relay. |
| `consumers.py` | Built-in subscribers: `audit_log`. E-mail and webhooks register the same way later without touching booking code. |
| `views.py`, `urls.py` | `GET /events` (added in Phase 8). |
| `migrations/0001_initial.py`, `0002_db_rules.py` | Tables, then the rules. `outbox` and `processed_events` have **no** row-level security on purpose: the worker reads across tenants and runs each event as its tenant. |

### `modules/booking/`

**Why the name:** the glossary's "booking"; the module list's `booking`.

| File | What it does |
| --- | --- |
| `models.py` | `BookingStatus` (the nine contract statuses, stored as-is), `Booking`, `BookingAllocation` (the time range a booking holds on a resource, effect HOLD or LOCK, `closed_at` when released). The allocation is a separate table so holds, locks and releases are rows, not status arithmetic. |
| `migrations/0003_db_rules.py` | The generated `during` range column and the **exclusion constraint**: two open allocations on one resource cannot overlap. This is what makes double booking impossible, even with many API containers. (`0001`/`0002` are the generated initial migrations, split by Django as in `config`.) |
| `lifecycle.py` | `MOVES`: the allowed `(from, move) → to` table copied from `docs/domain/booking.md`. `transition()` is the **only** code that changes `bookings.status`: look up the move (`INVALID_TRANSITION` otherwise), run its guards, update, run the effects of the new status (allocation HOLD/LOCK/close, timers), write one `transition_log` row, emit exactly one event. `Actor` says who moved it. Named after the domain doc's "lifecycle"; the plan had put it in `kernel/transitions.py`, but the lifecycle is booking knowledge and the kernel must not know bookings. |
| `service.py` | `evaluate()` (pipeline steps 1–6: validate, availability, eligibility, limits, approval, price; decides only), `create_booking()` (then step 7: save and start the lifecycle), `preview_booking()` (steps 1–6 as a dry run, which became `POST /bookings/preview` for free), the actions (`approve`, `reject`, `check_in`, `cancel`, later `check_out`), each a permission check plus `transition()`. |
| `serializers.py` | `CreateBookingRequest`, `PreviewBookingRequest`, `RejectBookingRequest`, `BookingListQuery`, and `booking_json()` (status, history, `appliedConfig`, payment). |
| `views.py`, `urls.py` | `/bookings`, `/bookings/preview`, `/bookings/{id}/approve|reject|check-in|check-out|cancel`. `POST /bookings` wraps the service call in `run_idempotent()`. |

Tests: `test_bookings.py`, `test_lifecycle.py` (every allowed move works, every other move is
`INVALID_TRANSITION`, one history row and one event each: 90 cases), `test_concurrency.py`
(two threads, one slot: exactly one 201 and one `SLOT_TAKEN`).

## Phase 6: the worker and timers

### `core/api/worker/`

**Why it exists:** timers (no-show, approval timeout, hold expiry) and outbox delivery need a
process that is not answering HTTP.
**Why a Django app:** a management command must live in an installed app; `worker` owns no
tables, only the command.
**Why one command, not two:** the plan had `relay_outbox` and `run_jobs`; both loops share one
poll cycle and one container, so `run_worker` runs both.

| File | What it does |
| --- | --- |
| `apps.py`, `__init__.py`, `management/__init__.py`, `management/commands/__init__.py` | Django app and command package markers. |
| `management/commands/run_worker.py` | The loop: `relay_batch()`, then `run_due_jobs()` (claims due `scheduled_jobs` with `FOR UPDATE SKIP LOCKED`, runs each inside `tenant_scope(job.tenant_id)` through its handler, marks done or retries with growing delays). Several workers can run side by side. `--once` runs one pass (tests). Stops cleanly on SIGTERM. `--reload` was added in Phase 11. |

### `modules/booking/jobs.py`

Registers `MARK_NO_SHOW`, `AUTO_COMPLETE`, `APPROVAL_TIMEOUT`, `EXPIRE_HOLD` with the kernel's
job runner; each calls `run_timer()`, which goes through `transition()` as `SYSTEM`. A
confirmed booking whose policy needs no check-in completes at its end (`AUTO_COMPLETE`), a
move the domain doc did not have ([open-decisions.md](open-decisions.md), item 4).
`booking/apps.py` imports it in `ready()` so the handlers register at start.

Tests: `test_worker.py`, `test_flow_end.py`.

## Phase 7: rules

#### `modules/rules/`

**Why the name:** `docs/domain/rules.md` and the module list.

| File | What it does |
| --- | --- |
| `models.py` | `RuleSetVersion`: every publish is an immutable snapshot of the tenant's whole rule set (no drafts). The one table the 24-table design did not have. |
| `jsonlogic.py` | A small JSONLogic evaluator (`evaluate`, `check`), no library, tested against the shared example `docs/examples/rule.json`. |
| `engine.py` | `evaluate_rules()`: pure evaluation of the rules in one pass, returning a `Decision` (denied reasons, `require_approval`, `require_payment`) with a trace. Deny beats allow; for duration and advance limits the more specific scope wins. No database access, so it is tested like a function. (Until 12 Nov 2026 it was `evaluate_stage()`, one call per stage; see build-history, Phase 12.) |
| `service.py` | `publish()` (checked with `check_rules()`: id, scope target exists, JSONLogic, consequence and limit, a price for scoped `require_payment`; with `baseVersion`), `current_rule_set()`, versions, `published_rules()` and `decide()`: what the booking pipeline's steps 3–5 call. The booking stores the version it was checked against in `appliedConfig.ruleSetVersion`. |
| `views.py`, `urls.py` | `/rules`, `/rules/versions`, `/rules/versions/{v}`. |
| `migrations/0001_initial.py`, `0002_db_rules.py` | Table and RLS. |
| `migrations/0003_rule_shape_v2.py` | Phase 12: rewrites stored rule sets to the second shape, tenant by tenant (the app role has no `BYPASSRLS`). |

Tests: `test_rules_engine.py`, `test_rules_api.py`.

## Phase 8: completing the contract (16 → 59 operations)

Once the demo flow ran, every engine was given the endpoints a product would need. Most of
this phase added functions to existing files; the new files were:

| File | Why | What it does |
| --- | --- | --- |
| `modules/payments/` (whole module) | The lifecycle's payment hook could not be tested without payments, and the contract had a payment policy | See below. |
| `kernel/history.py` | Status changes of resources, payments, refunds and memberships had to be audited like bookings | `record_status()` and `history_of()`: `transition_log` rows for every object other than bookings, written in the same transaction. |
| `modules/events/views.py`, `urls.py` | Products and the console need to read events | `GET /events`. |

#### `modules/payments/`

**Why the name:** the module list had `pricing`; what was needed was payment *state* (a
payment, its events, refunds). The price itself is computed in the booking pipeline's step 6
through `payments.service.quote()`.

| File | What it does |
| --- | --- |
| `models.py` | `Payment` (per booking, with status), `PaymentEvent` (every gateway message, kept), `Refund`. |
| `service.py` | `quote()`, `start_payment()`, `mark_paid()` (front desk), `record_webhook()` (the mock gateway: HMAC-SHA256 over the raw body in `X-Signature`; duplicates and forged signatures rejected), refunds by policy, `expire_pending()`, `reconciliation_queue()`. Standard library only, no gateway SDK. |
| `views.py`, `urls.py` | `/payments/{id}`, `/payments/{id}/mark-paid`, `/refunds/{id}/mark-succeeded`, `/payments/reconciliation`, `/webhooks/payments/{gateway}/tenants/{tenantId}`. |
| `migrations/0001`–`0004` | Tables and rules, in two rounds: payments first, then `payment_events` and `refunds`. |

Also in this phase: sites' hours and exceptions, resource status moves, adding and archiving
fields, policy version history and restore, people (roles, invitations, disable, enable),
check-out. The contract grew additively; a script checked that every old key and value
survived. Tests: `test_payments.py`, `test_people.py`.

## Phase 9: sign-in (D-003)

The docs assumed an external auth service that did not exist.

#### `modules/identity/`

**Why a new module and not part of `users`:** `users` answers "who may do what in a tenant";
`identity` answers "is this really that person" (passwords, tokens, links). The rest of the
core only verifies tokens, so issuing them is one replaceable module.
**Why the name:** the usual term for that concern; `auth` was avoided because
`kernel/auth.py` already verifies tokens.

| File | What it does |
| --- | --- |
| `models.py` | `Credential` (PBKDF2 password hash, failed attempts, lock), `RefreshToken` (stored as SHA-256, single use, family for reuse detection), `OneTimeToken` (password reset and invitation links, `LinkPurpose`). Three tables, which with `rule_set_versions` make 28. |
| `service.py` | `register`, `login` (same 401 for unknown e-mail and wrong password; lock after 5 failures), `refresh` (rotation; reusing a used token ends the session), `logout`, `change_password`, `forgot_password`, `reset_password`, `accept_invitation`, `guest` (2-hour token, `guest` role), `tenants_of`. Tokens are signed with `kernel/devtokens.sign()`. |
| `consumers.py` | Sends the invitation e-mail on `member.invited`, from the worker. The link's secret exists only in the e-mail. |
| `views.py`, `urls.py` | `/auth/register|login|refresh|logout|password/*|invitations/accept|guest`, `/me/tenants`; throttled per client address (`AUTH_RATE`). |
| `management/commands/auth_link.py` | Prints a fresh reset or invitation link locally, where e-mail goes to the log. |
| `migrations/0001_initial.py` | The three tables. They are not tenant tables: a person signs in before choosing a tenant. |

Also: `modules/users/migrations/0003_own_memberships.py`, the one RLS exception (a person may
read their own memberships while no tenant is active, for `/me/tenants`). Building this
exposed a real bug: the tenant `ContextVar` leaked between requests on one thread; fixed in
`kernel/request_context.py` (`RequestIdMiddleware` resets it) with a regression test.
Tests: `test_identity.py`. Contract: 69 operations.

## Phase 10: proof and tooling

| File | Why | What it does |
| --- | --- | --- |
| `app/docs.py` | People needed to try the API without Postman | The docs hub at `/api/docs`: sign-in, tenant picker, Swagger with the token and tenant filled in, ReDoc, every markdown file of the repository and the notes folder. Local only; never serves `.env` or Postman environments. Test: `test_docs_pages.py`. |
| `modules/tenancy/management/commands/seed_demo.py` | A realistic tenant for demos and the Postman scenario | 2 sites, 3 resource types, 7 resources, rules, 5 people with one printed password; everything through the same service functions as the API. Test: `test_seed_demo.py`. |
| `app/settings/__init__.py` | Configuration in one `.env` file, like `paihong_apis` | Loads `core/api/.env` with the standard library before any settings module; shell variables win. |
| `.env.example` | The documented template | Every variable with a comment; `dev.py up` copies it to `.env` on the first run. Compose reads the same file through `--env-file`. |

Outside the code: the Postman scenario (notes folder) reached 198 requests covering all 69
operations; a traced run produced [api-table-map.md](api-table-map.md).

## Phase 11: dependencies with uv, hot reload (10/11)

The run was simpler than before but still behind `paihong_apis` in two ways: no lock file
(two builds could install different versions) and no live code reload in the containers.

| File | Change | Why |
| --- | --- | --- |
| `pyproject.toml` | Gained `[project]` (runtime dependencies), `[dependency-groups] dev`, `[tool.uv] package = false` | The standard place for dependencies (PEP 621). `package = false`: an application, never built as a library. |
| `uv.lock` | New, committed | Exact versions of every package, the same for the image, CI and every laptop. |
| `.python-version` | New: `3.12` | The Python uv uses, the same as the image. |
| `requirements.txt`, `requirements-dev.txt` | Deleted | Replaced by the two files above. |
| `Dockerfile` | uv copied from its pinned image; `uv sync --locked --no-dev` into `/opt/venv` | Locked installs; the virtualenv sits outside `/app` so the source can be mounted over `/app`. |
| `infra/compose.dev.yaml` | New, local only | Mounts `core/api` over `/app`; `gunicorn --reload`; `run_worker --reload`. CI starts `compose.yaml` alone, where a mount would break Docker-in-Docker. |
| `worker/.../run_worker.py` | `--reload` | Django's own reloader (as `runserver` uses) restarts the loop on a file change. The loop then runs in a thread, so signal handlers are set only in the main thread. |
| `scripts/dev.py` | Adds `compose.dev.yaml`; `check` runs every tool through `uv run --locked` | No separate virtualenv step. |
| `.gitlab-ci.yml` | `pip install uv`, `uv sync --locked`, cache keyed on `uv.lock` | The same versions as the image. |

## The finished tree

```text
core/api/
├── manage.py  pyproject.toml  uv.lock  .python-version  Dockerfile  .dockerignore  .env.example  README.md
├── app/                       Phase 1, 10   the Django project
│   ├── settings/              __init__ (.env loader), base, local, test, production
│   ├── urls.py  wsgi.py  docs.py
├── kernel/                    Phase 2, 5, 8 shared layer; imports no module
│   ├── uuid7 models db tenant_context errors pagination params serializers
│   ├── request_context cors auth access permissions devtokens
│   ├── idempotency jobs history
│   ├── management/commands/dev_token.py
│   └── migrations/            0001_initial, 0002_db_rules
├── modules/
│   ├── tenancy/               Phase 2   tenants; create_tenant, add_member, seed_demo (Phase 10)
│   ├── users/                 Phase 2   people, memberships, roles, grants
│   ├── resources/             Phase 3   sites, resource types, resources
│   ├── config/                Phase 3   policy versions, custom fields
│   ├── availability/          Phase 4   hours, exceptions, free slots
│   ├── events/                Phase 5   outbox, subscribers, GET /events
│   ├── booking/               Phase 5   pipeline, lifecycle, timers
│   ├── rules/                 Phase 7   rule sets, JSONLogic, engine
│   ├── payments/              Phase 8   payments, webhooks, refunds
│   └── identity/              Phase 9   passwords, tokens, links
├── worker/                    Phase 6   run_worker
└── tests/                     Phase 2 → 19 files, 260 tests
infra/compose.yaml  infra/compose.dev.yaml  infra/postgres/init.sql  scripts/dev.py
```

## What changed from the plan, and why

| Planned | Built | Why |
| --- | --- | --- |
| Flask + SQLAlchemy + Alembic (`docs/backend.md`) | Django + DRF + Django migrations | The team's experience; proposed decision D-002, not yet approved |
| `kernel/transitions.py` | `modules/booking/lifecycle.py` | The lifecycle is booking knowledge; the kernel must not know bookings |
| `kernel/tenancy_middleware.py` | `kernel/access.py: TenantAPIView` | The tenant check needs the authenticated user, which DRF resolves inside the view, not in Django middleware |
| camelCase renderer or library | Explicit `*_json()` functions | Responses are assembled from several tables anyway; no new dependency |
| `relay_outbox` + `run_jobs` commands | One `run_worker` | One container, one poll loop |
| `selectors.py` per module | `*_qs()` functions in `service.py` | Fewer files; the boundary that matters is the module, not the file |
| `events.py` per module | Event names next to the code that emits them | Nothing else read the list |
| `pricing`, `notifications` modules | `payments.service.quote()`; subscribers in `events/consumers.py`, `identity/consumers.py` | Nothing yet that needed a module of its own |
| External auth service | `modules/identity` | There was no such service (D-003) |
| 24 tables | 28 | `rule_set_versions` and the three sign-in tables |
| Payments after the demo | Built, with a mock gateway | The lifecycle's payment hook could not be tested without it |
| `requirements*.txt` | `pyproject.toml` + `uv.lock` | A lock file, and the tool the team chose (Phase 11) |

## Keeping this page true

When you add a folder or a file that a reader would look for, add it to the phase where it
belongs (or a new phase at the end), with why it exists and why it has its name, and update
[structure.md](structure.md). [build-history.md](build-history.md) keeps the short version.
