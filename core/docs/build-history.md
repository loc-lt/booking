# How the backend was built

`core/core/` held one file, `CLAUDE.md`, pointing at `docs/backend.md`, when backend work
started on 2026-11-02. The frontend had been working for two weeks against generated mocks,
the contract had 16 operations, and CI already expected `core/api/requirements-dev.txt`,
`ruff`, `lint-imports`, `pytest core/api/tests` and a Docker build of `core/api`. This page
records the order things were built in and why, so a reader can tell a deliberate shape from
an accident; [build-walkthrough.md](build-walkthrough.md) tells the same story folder by
folder and file by file. The plan it followed is the team's `KE_HOACH_CODE_BE.md` (notes folder,
Vietnamese); the first commit, `fix: backend core APIs`, landed everything up to the auth
module.

## Phase 0: decisions before code

Two sources disagreed before a line was written: `docs/backend.md` described Flask,
SQLAlchemy, Alembic and a table set (`field_defs`, `config_versions`, `booking_events`), while
the team's database design had 24 tables and the team's experience was Django. The choice was
Django + DRF with the 24-table design, recorded as proposed decision **D-002** and a list of
open items ([open-decisions.md](open-decisions.md)). Also settled here: the database stores the
contract's nine booking statuses rather than the seven of the DBML, which makes `transition()`
a direct copy of the table in `docs/domain/booking.md`.

What was reused from an earlier Django prototype (`backend/rise`, since deleted): the UUIDv7
helper, `BaseModel`/`TenantModel`, the migration helpers for RLS and same-tenant keys, the
tenant context, the custom-field compiler idea, and the outbox relay. Each moved into
`kernel/` or `modules/config/` with imports fixed; nothing else was copied.

## Phase 1: the skeleton (03/11)

Created in this order so that each step could be checked:

1. `requirements*.txt`, `pyproject.toml` (ruff, pytest, the two import-linter contracts).
   The contracts came first so the module boundary existed before any module did.
2. `manage.py`, `app/settings/{base,local,test,production}.py`: all configuration from
   environment variables, `ATOMIC_REQUESTS=True`, `USE_TZ=True`, DRF pointed at our
   authentication class and exception handler before either existed.
3. `app/urls.py` with `GET /api/healthz` running `SELECT 1`.
4. `Dockerfile` (one image, Gunicorn default command), `infra/compose.yaml` (Postgres 17 with
   `init.sql` creating the non-superuser role, `migrate`, `api`, `worker`),
   `scripts/dev.py` so that Windows, macOS and Linux share one way to run things.

Done when Compose came up, `/api/healthz` answered 200, and ruff was clean.

## Phase 2: kernel, tenants, people (04–05/11)

Everything later needs a JWT and a tenant, so this came before any business table.

1. `kernel/uuid7.py`, `kernel/models.py`, `kernel/db.py`, `kernel/tenant_context.py`.
2. `kernel/errors.py` with one class per contract code and `problem_handler()`, so that DRF's
   own validation errors already came out as RFC 9457 from day one.
3. `kernel/pagination.py` (cursor), `kernel/params.py`, `kernel/serializers.py`.
4. `modules/tenancy` (`tenants`) and `modules/users` (`users`, `memberships`, `roles`,
   `role_permissions`, `membership_roles`), without the links to `locations`, which did not
   exist yet; they came with Phase 3 (the committed migrations are in their final shape).
5. `kernel/auth.py` (`AuthAdapter`, `JWTAuthentication`) and `kernel/access.py`
   (`TenantAPIView`), `kernel/permissions.py` with the permission codes, `users/constants.py`
   with the five system roles.
6. `kernel/devtokens.py` and `dev_token`, so the frontend could call the real API before any
   sign-in existed; `create_tenant`, `add_member`.
7. Tests: expired, wrongly signed and wrong-audience tokens → 401; non-member → 403; tenant A
   cannot read tenant B. `conftest.py` learned to switch to a non-superuser role so these
   tests mean something in CI.

## Phase 3: resource types, policies, fields, resources (05–06/11)

The console already had screens for resource types, so the first business endpoints were
theirs. `modules/resources` and `modules/config` were built together because the contract's
`ResourceType` is assembled from three tables (`resource_types`, `policy_versions`,
`field_definitions`). `config/policy.py` became the two-way map between the contract's
`flowConfig` and the stored body (seconds inside, minutes outside), and gained the
`cancellation.allowedUntilMinutesBefore` key the design lacked. `config/fields.py` compiles
definitions to JSON Schema with `pattern` instead of `format` so Ajv in the browser and
`jsonschema` on the server agree. `STALE_VERSION` on `baseVersion`, immutable versions, and
"a no-op edit publishes nothing" were decided here. Sites (`POST /sites`, hours) were added
to the contract at this point because the design needed them and no screen had asked.

## Phase 4: availability (09–10/11, done early)

`availability_rules` in local wall-clock time with the site's timezone; `open_intervals()`
subtracts exceptions and adds buffers; `free_slots()` cuts to the type's slot length. The
free-slot search needed resources, availability and bookings at once, so it lives in
`availability/search.py` with imports pointing one way, not in `service.py`.

## Phase 5: the pipeline, `transition()`, no double booking

The part the demo cannot lose, built in this order:

1. `kernel/models.py` gained `TransitionLog`, `ScheduledJob`, `IdempotencyKey`;
   `modules/events` gained `Outbox`, `ProcessedEvent` and `emit_event()`.
2. `booking/models.py` with `Booking` and `BookingAllocation`; `booking/migrations/0003_db_rules.py`
   with the generated `during` range and the exclusion constraint. The allocation is a
   separate table so that holds, locks and releases are rows with `closed_at`, not booking
   status arithmetic.
3. `booking/lifecycle.py`: `MOVES` copied from the domain doc, `transition()` as the single
   writer of `status`, effects for allocations and timers, one history row, one event.
4. `booking/service.py`: `evaluate()` (steps 1–6, pure decision) and `create_booking()`
   (step 7). `preview_booking()` fell out for free and became `POST /bookings/preview`.
5. `kernel/idempotency.py` and the `Idempotency-Key` requirement on `POST /bookings`.
6. Tests: the two-thread race (exactly one 201, one `SLOT_TAKEN`), replay by key, the 90-case
   lifecycle matrix.

The actions (`approve`, `reject`, `check_in`, `cancel`, later `check_out`) followed as
functions that check permission and call `transition()`.

## Phase 6: worker and timers

`worker/management/commands/run_worker.py` runs both loops in one process (the plan had two
commands); `kernel/jobs.py` registers handlers by job type; `booking/jobs.py` registers
`MARK_NO_SHOW`, `AUTO_COMPLETE`, `APPROVAL_TIMEOUT`, `EXPIRE_HOLD`. A confirmed booking whose
policy needs no check-in completes at its end (`AUTO_COMPLETE`), a move the domain doc did
not have ([open-decisions.md](open-decisions.md), item 4).

## Phase 7: rules

`modules/rules` with one table, `rule_set_versions`: every publish is an immutable snapshot of
the whole set (no drafts), checked at publish against the fixed context and effect list.
`rules/jsonlogic.py` is a small evaluator (no library) tested against the shared example
`docs/examples/rule.json`; `rules/engine.py` is pure. The pipeline's steps 3–5 call
`check_rules()`; the booking stores the rule set version in `appliedConfig.ruleSetVersion`.

## Phase 8: completing the contract (16 → 59 operations)

Once the demo flow ran, every engine was given the endpoints a product would need: sites and
hours, exceptions, resource status moves, adding and archiving fields, policy version history
and restore, people (roles, invitations, disable/enable), payments (`payments`,
`payment_events`, `refunds`, `mark-paid`, the mock gateway webhook with HMAC, refunds by
policy, reconciliation), `GET /events`, check-out. The contract grew additively; a script
checked that every old key and value survived. The Postman scenario in the notes folder grew
with it and started checking each response against the contract's schema.

## Phase 9: sign-in (D-003)

The docs assumed an external auth service that does not exist. `modules/identity` was added
with passwords, refresh-token rotation and reuse detection, lockout, one-time links for
password reset and invitations, guest tokens, `/me/tenants` (which needed the one RLS
exception, `own_memberships`). Finding this exposed a real bug: the tenant `ContextVar` leaked
between requests on one thread; fixed in `RequestIdMiddleware` with a regression test.
Contract: 69 operations.

## Phase 10: proof and tooling

- The docs hub at `/api/docs` (`app/docs.py`): Swagger with the token and tenant filled in,
  every markdown file in the browser.
- `seed_demo` producing a realistic tenant with one password for everyone.
- The Postman scenario reached 198 requests covering all 69 operations; a traced run produced
  the measured API → table map ([api-table-map.md](api-table-map.md)) and the flow diagram in
  the notes folder.
- Configuration moved to one `.env` file read by Django, Compose and `dev.py`.

## Phase 11: uv and hot reload (10/11)

Dependencies moved from `requirements*.txt` to `pyproject.toml` + a committed `uv.lock`
(same versions in the image, CI and on laptops). `infra/compose.dev.yaml`, added only by
`dev.py`, mounts the source into the containers with `gunicorn --reload` and
`run_worker --reload`, so an edit no longer needs a rebuild.

## What changed from the plan, and why

| Planned | Built | Why |
| --- | --- | --- |
| `kernel/transitions.py` | `modules/booking/lifecycle.py` | The lifecycle is booking knowledge; the kernel must not know bookings |
| `kernel/tenancy_middleware.py` | `kernel/access.py: TenantAPIView` | The tenant check needs the authenticated user, which DRF resolves inside the view, not in Django middleware |
| camelCase renderer or library | Explicit `thing_json()` functions | Responses are assembled from several tables anyway; no new dependency |
| `relay_outbox` + `run_jobs` commands | One `run_worker` | One container, one poll loop |
| `selectors.py` per module | `*_qs()` functions in `service.py` | Fewer files; the boundary that matters is the module, not the file |
| `events.py` per module | Event names next to the code that emits them | Nothing else read the list |
| External auth service | `modules/identity` | There was no such service (D-003) |
| 24 tables | 28 | `rule_set_versions` and the three sign-in tables |
| Payments after the demo | Built, with a mock gateway | The lifecycle's payment hook could not be tested without it |
| `requirements*.txt` | `pyproject.toml` + `uv.lock` | A lock file, and the tool the team chose (Phase 11) |
