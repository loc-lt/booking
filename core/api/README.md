# Booking core API (Django)

The backend of `contracts/openapi.yaml` (59 operations): API and worker, one image. Docs that
govern it: [docs/backend.md](../../docs/backend.md), [docs/api.md](../../docs/api.md),
[docs/domain/](../../docs/domain/).

> **Needs decision D-002 before merge.** `docs/backend.md` and `docs/architecture.md` still say
> Flask + SQLAlchemy + Alembic. This code is Django + DRF. See "Open decisions" below.

## Run it

From the repository root, with Docker running and Python 3.10+:

```bash
python scripts/dev.py up        # postgres :55433, migrate, API :8000, worker; waits for /api/healthz
python scripts/dev.py seed      # demo tenant: 2 sites, 3 resource types, 7 resources, rules, people
                                # + one password for all of them (POST /api/v1/auth/login) + dev tokens
python scripts/dev.py token someone --email someone@demo.test   # a 12-hour dev JWT
python scripts/dev.py timers <tenantId>   # make that tenant's pending timers due now
python scripts/dev.py check     # what CI runs: ruff, import contracts, pytest
python scripts/dev.py docs      # opens http://localhost:8000/api/docs
python scripts/dev.py help      # everything else (logs, psql, down, reset)
```

**Docs in the browser: <http://localhost:8000/api/docs>**: Swagger UI (try every endpoint;
paste a token and tenant id once), ReDoc, the raw contract, and every markdown doc of the repo
(plus the team's `docs/` folder next to it, when started with `dev.py up`). Served by
`app/docs.py`, local only (`API_DOCS_ENABLED`).

```bash
curl http://localhost:8000/api/v1/resource-types \
  -H "Authorization: Bearer <token>" -H "X-Tenant-Id: <tenantId>"
```

Sign in like an app does: `POST /api/v1/auth/login` with an email printed by `seed` and its
password, or use the login form at <http://localhost:8000/api/docs>. Invitation and reset emails
are printed in the logs (`python scripts/dev.py logs worker`); `python scripts/dev.py manage
auth_link reset --email <email>` prints a fresh link.

`seed` and `token` run inside the api container with local settings (DEBUG on), so they can
mint development tokens; the server itself runs with production settings. Platform commands:
`create_tenant` (a tenant with roles, a site and an owner) and `add_member`.

Tests need the database only (`docker compose -f infra/compose.yaml up -d postgres`) and a
virtualenv: `python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt`
(`bin/pip` on macOS/Linux). `pytest core/api/tests` runs ~240 tests against real PostgreSQL.

## Layout

```text
app/          settings (base, local, test, production), urls (/api/healthz, /api/v1/...)
kernel/       shared by every module, imports no module
  auth.py           AuthAdapter: JWT signature, exp, iss, aud (JWKS or HS256)
  access.py         TenantAPIView: X-Tenant-Id -> SET LOCAL app.tenant_id -> membership -> Access
  permissions.py    the 27 permission codes (GET /permissions)
  errors.py         RFC 9457 problem details with the contract's codes
  history.py        transition_log rows for resources, payments, memberships
  pagination.py     ?limit&cursor -> {data, nextCursor}
  idempotency.py    Idempotency-Key, stored in the request transaction
  jobs.py           scheduled_jobs: schedule, cancel, handler registry
  devtokens.py      development JWTs (DEBUG only)
  db.py             migration helpers: enable_rls, same_tenant_fk, attributes_check
modules/      one Django app each; other modules may import only its service.py
  tenancy/          tenants; commands create_tenant, add_member, seed_demo
  identity/         sign-in (D-003): passwords, refresh tokens, invitation and reset links,
                    guest tokens; /auth/*, /me/tenants; command auth_link
  users/            memberships, roles, invitations, access; /me, /roles, /members
  resources/        sites, resource types, resources; their endpoints
  config/           policy versions (flowConfig <-> body), custom fields -> JSON Schema
  availability/     opening hours (site or resource), exceptions, free slots
  booking/          the pipeline (evaluate + create + preview), lifecycle, payment side
  payments/         payments, payment_events, refunds; mock gateway webhooks
  rules/            rule_set_versions; JSONLogic evaluator and rule engine
  events/           outbox, processed_events, subscribers; GET /events
worker/       run_worker: outbox delivery + due timers
tests/        everything CI runs (pytest core/api/tests)
```

Each request: JWT -> tenant + membership -> view checks permission -> request serializer ->
**one** service function in one transaction (writes + transition_log + outbox) -> response.

## The engines

| Engine | Where | What it guarantees | Proven by |
| --- | --- | --- | --- |
| Tenancy | `kernel/access.py`, `kernel/db.py`, `*/migrations/*_db_rules.py` | RLS on every tenant table, FORCE'd; same-tenant composite FKs | `test_auth_and_tenancy.py` |
| Sign-in | `modules/identity/` | Email + password (PBKDF2); 15-minute access JWTs; single-use refresh tokens, reuse ends the session; lockout after 5 wrong passwords; same answer for unknown email; emailed one-time links stored hashed; guest tokens | `test_identity.py` |
| People and access | `modules/users/` | Roles = permission codes, scoped per site; system roles follow the code; invitations claimed only with a verified email; disabled members lose access at once | `test_people.py` |
| Config versions | `modules/config/`, `resources/service.py` | Policies versioned; stale `baseVersion` → `STALE_VERSION`; bookings keep their version; restore = republish as newest; no-op edits publish nothing | `test_resource_types.py`, `test_config_flex.py` |
| Custom fields | `modules/config/fields.py` | Field definitions → JSON Schema (patterns, not formats, so Ajv agrees); add or archive later without rewriting records; keys permanent | `test_resource_types.py`, `test_config_flex.py` |
| Availability | `modules/availability/` | Site or resource hours in local time, compared in UTC; DST-safe; blocks and extra openings; buffers | `test_availability.py`, `test_sites_and_resources.py` |
| Pipeline | `booking/service.py:evaluate`, `create_booking`, `preview_booking` | The seven steps in order; denials name the setting or rule; preview = steps 1-6 without writing | `test_bookings.py`, `test_rules_api.py` |
| Rules | `modules/rules/` | Versioned rule sets; checked on publish; JSONLogic subset; deny beats allow; specific scope wins; quotas from usage; trace | `test_rules_engine.py`, `test_rules_api.py` |
| Double booking | `booking/migrations/0003_db_rules.py` | Exclusion constraint on open allocations; races → `SLOT_TAKEN` (incl. the deadlock case) | `test_concurrency.py` |
| Lifecycle | `booking/lifecycle.py:transition` | Only path that changes status; one history row + one event per move | `test_lifecycle.py` (90 cases), `test_flow_end.py` |
| Payments | `payments/service.py`, `booking/service.py` (payment side) | Upfront payment holds the slot; desk or signed webhook pays once (duplicates ignored); expiry; refunds by policy; reconciliation queue | `test_payments.py` |
| Outbox + worker | `events/service.py`, `worker/` | Event saved with the change; delivered once per subscriber; retries, then parks | `test_worker.py` |
| Timers | `kernel/jobs.py`, `booking/jobs.py` | no-show, auto-complete, approval timeout, hold expiry, all via `transition()` | `test_worker.py`, `test_payments.py`, `test_flow_end.py` |

The Postman scenario in the workspace (`docs/postman/`, 198 requests covering all 69 operations) also checks every response
body against this contract's schema for that path, method and status.

## Open decisions (raise in the decision MR)

1. **D-002 Django instead of Flask.** Changes `docs/backend.md` (structure, libraries,
   migrations) and `docs/architecture.md`. CI already adapted: `lint-imports` runs inside
   `core/api`, deploy runs `python manage.py migrate`.
2. **Statuses.** The database stores the contract's nine statuses (`confirmed`, ...), not
   the seven of `booking_core_mvp.dbml`. `create_target` was dropped from the policy body.
3. **New policy keys** `cancel_allowed_until_seconds`, and `flowConfig.limits`, `buffers`,
   `payment` exposing keys the body already had (`price` became `{amount_minor, per}`;
   `refund_rules` `[{before_seconds, percent}]`).
4. **Check-in not required → the booking completes at its end** (`AUTO_COMPLETE`, a new
   `confirmed → completed` move, timer only). `docs/domain/booking.md` needs the row.
5. **No RLS on** `scheduled_jobs`, `outbox`, `processed_events`: the worker scans across
   tenants and runs each item inside its tenant. Only code writes them; `GET /events`
   filters by tenant explicitly.
6. `users.email` **is nullable**: guests may give no email. Invitations create a placeholder
   user (`auth_subject = invite|<email>`); the emailed link (`/auth/invitations/accept`) sets
   its password. A token from another issuer with that email and `email_verified: true` can
   also claim it (external provider, dev tokens).
7. **Members' cancellation deadline doesn't bind staff** (`booking.cancel_any`); staff
   cancellations refund 100%.
8. **Rule storage: one new table `rule_set_versions`** (outside the 24 MVP tables): every
   publish is an immutable snapshot of the whole rule set, no drafts.
9. **System roles take their permissions from code** (`users/constants.py`), not from
   `role_permissions`, and cannot be edited through the API.
10. **New events** to add to `docs/domain/events.md`: `member.invited|joined|disabled|enabled|
    roles_changed`, `payment.session_created|paid|failed|expired|reconciliation_needed`,
    `refund.requested|succeeded`. Resource status changes use `resource.updated`.
11. **Webhook path** `/webhooks/payments/{gateway}/tenants/{tenantId}`: the one place the tenant
    comes from the URL (payments are behind RLS; the gateway sends no JWT). Mock gateway
    only, signed with `PAYMENT_WEBHOOK_SECRET` (HMAC-SHA256).
12. **Contract** grew from 16 to 69 operations, additively. Needs the frontend's `pnpm gen`
    (CI diffs the generated client) and one frontend + one backend + lead approval.

13. **D-003: the core signs people in** (proposed in `docs/decisions.md`). New tables
    outside the 24 MVP tables: `user_credentials`, `refresh_tokens`, `auth_tokens` (no tenant,
    no RLS, like `users`). `docs/architecture.md` and `docs/operations.md` still name an
    external auth service. Tokens are HS256 for now; RS256 + JWKS before products verify
    tokens themselves.

## Dependencies

| Package | Why | Alternative considered |
| --- | --- | --- |
| Django, djangorestframework | Web framework, request validation (team's Django experience) | Flask + Pydantic (the docs' original plan) |
| psycopg[binary] | PostgreSQL driver | — |
| PyJWT[crypto] | Token verification (docs/backend.md) | — |
| jsonschema | Custom field and policy validation (docs/backend.md) | — |
| gunicorn | Serving (docs/backend.md) | — |
| pytest, pytest-django, ruff, import-linter | Tests and CI checks | — |

No camelCase library (serializers use the contract's names), no JSONLogic library (a small
evaluator in `modules/rules/jsonlogic.py`, tested against the shared example) and no payment
SDK (the mock gateway is HMAC over the raw body, standard library only).
