# Backend guide

For anyone working in `core/`. Shared rules live in the root [CLAUDE.md](../CLAUDE.md); API rules in [api.md](api.md); domain behaviour in [domain/](domain/).

## Structure

One Flask app in `core/api/`. Each core module is a package under `core/api/modules/` (tenancy, users, resources, availability, booking, rules, pricing, config, notifications, events). The worker lives in `core/api/worker/` and runs from the same image.

Each module has:

| File | Holds |
| --- | --- |
| `api.py` | Flask blueprint: routes only, no business logic |
| `service.py` | The public interface other modules may call |
| `models.py` | SQLAlchemy models, private to the module |
| `schemas.py` | Pydantic request and response models, mirroring the contract |
| `events.py` | Events the module emits |

## Rules

- A module may import another module's `service.py` only. import-linter enforces it.
- A route parses input, calls **one** service function, and returns a response model.
- A service function runs in one transaction; any change writes its events to the outbox in that same transaction.
- Booking status changes only through `transition()`.
- Keep functions small and single-purpose; tests ship in the same merge request.
- Migrations: Alembic, run as a separate deploy step, never at app start. Backward compatible for one release: add, deploy, remove later.
- Logs: JSON to standard output, with request id and tenant id on every line.

## Libraries

| Concern | Choice |
| --- | --- |
| Database | SQLAlchemy 2, Alembic |
| Validation | Pydantic v2; `jsonschema` for custom fields |
| Rules | A JSONLogic evaluator |
| Auth | PyJWT |
| Contract checks | Schemathesis |
| Boundaries | import-linter |
| Lint and format | ruff |
| Tests | pytest |
| Serving | Gunicorn behind Caddy |

## Data and tenancy

- Every table has `tenant_id`, filtered by row-level security policies. Example: [examples/sql/tenant-isolation.sql](examples/sql/tenant-isolation.sql).
- After verifying the JWT and the user's membership in the requested tenant, the API sets the tenant for the transaction (`SET LOCAL app.tenant_id`).
- The app connects as a role that does **not** own the tables; owners bypass row-level security unless it's forced.
- Double bookings are impossible: an exclusion constraint on resource and time range rejects the second of two racing requests, and the API returns `SLOT_TAKEN`. Example: [examples/sql/no-double-booking.sql](examples/sql/no-double-booking.sql). Shared-capacity spaces use a row-locked counter instead.
- IDs are UUIDv7. Timestamps are `timestamptz`.

| Table | Holds |
| --- | --- |
| `resource_types` | Field definitions (`field_defs`), policies (`flow_config`), `version` |
| `resources` | Custom field values in `attributes` (JSONB, GIN index), `definition_version` |
| `config_versions` | Every draft and published version of settings and rules |
| `bookings` | `during` (time range), `status`, `payment_status`, `applied_config` |
| `booking_events` | Booking history: from, to, actor, reason |
| `attribute_history` | Previous custom field values |
| `outbox` | Events waiting for delivery |
| `scheduled_jobs` | Timers: no-shows, approval timeouts, payment-hold expiry |

## Auth

The core signs people in itself (decision D-003): module `modules/identity`, endpoints under `/api/v1/auth/`. It issues JWTs; every other endpoint only verifies them, so the rest of the core does not care who issued a token.

- **Email + password.** Hashed with Django's PBKDF2 hasher, checked by Django's password validators (8+ characters, not common, not all digits). Passwords and tokens are never stored in clear: refresh tokens and emailed links are stored as SHA-256 hashes.
- **Tokens.** A short access token (15 minutes, `AUTH_ACCESS_TTL_SECONDS`) and a refresh token (30 days) that works once: `/auth/refresh` returns a new pair. Reusing an already used refresh token ends that whole session (it has probably leaked). Logout, password change and password reset end sessions too.
- **Brute force.** Unknown email and wrong password get the same 401. After 5 wrong passwords the account locks for 15 minutes. Sign-in endpoints are rate-limited per client address (`AUTH_RATE`).
- **Accounts.** Members and guests register themselves (`/auth/register`). Staff and admins are invited (`POST /members/invite`); the worker emails a one-time link, and `/auth/invitations/accept` sets the password and activates the membership. An address with a pending invitation cannot register: the link is the way in.
- **Guest (no-account) booking.** `/auth/guest` gives a short-lived access token (2 hours, no refresh token) for a new member with the `guest` role in one tenant, unless the tenant turned guests off (`settings.guestBooking`). There is still no unauthenticated path to the booking API.
- **Verify every token:** signature, `exp`, `iss`, `aud`, in one `AuthAdapter` class. Tokens are HS256 with `JWT_SECRET` from the server's `.env`; plan a move to asymmetric keys (RS256) with a JWKS endpoint before products verify tokens themselves. An external identity provider can still be plugged in through `JWT_JWKS_URL`.
- **Map the user:** `sub` maps to a core user. `GET /me/tenants` lists the person's tenants (an RLS policy allows reading one's own memberships only while no tenant is active).
- **Tenant and role come from the core:** the user's membership in the tenant named by `X-Tenant-Id`. One person can belong to several tenants.
- **Roles per tenant:** `owner`, `admin`, `staff`, `member`, `guest`; optionally scoped to a site.
- **Email.** Invitation and reset emails are sent after commit through Django's mail backend: console locally (the worker or API log), SMTP on servers (`EMAIL_*`).
- **Service tokens** for product backends (after December) are JWTs with a `scope` claim.

## Engine

### `transition()`

Looks up the move in the lifecycle table ([domain/booking.md](domain/booking.md)) and raises `INVALID_TRANSITION` if it's not allowed. Then it runs the hooks for the target status (rules, payment, check-in window), which may deny with reasons. Finally it updates the status, writes a `booking_events` row and adds the event to the outbox, all in the request's transaction. The payment hook has one implementation for December: `NoPayment`.

### Rules

Evaluation follows [domain/rules.md](domain/rules.md). Published rule sets are cached per tenant and refreshed on `config.published`.

### Worker

- **Outbox delivery:** picks up undelivered events with `FOR UPDATE SKIP LOCKED`, hands each to its subscribers, and marks it delivered. Failures retry with growing delays and are parked with an alert after a set number of attempts.
- **Timers:** runs due `scheduled_jobs`, each through `transition()`.
- **Duplicates:** each subscriber records processed event ids and skips repeats.

## Testing

Tests are written together with the code, in the same merge request. Backend functions are small and fully specified, so tests are cheap and catch the costliest bugs early. Agents write them as part of the task.

| Area | Must have |
| --- | --- |
| Lifecycle | Every allowed move works; every other move raises `INVALID_TRANSITION`; each move writes history and one event |
| Rules | The shared example file passes; deny beats allow; traces are correct |
| Double booking | Two parallel requests for one slot: exactly one succeeds (real PostgreSQL) |
| Tenancy | Tenant A can't read or change tenant B's data through any endpoint |
| Auth | Expired, wrongly signed and wrong-audience tokens are rejected; non-members get `FORBIDDEN` |
| Time | Daylight-saving changes and midnight in the site's timezone |
| Contract | Responses match `openapi.yaml` (Schemathesis) |
| Worker | A duplicate event is processed once; failures retry |
| Seeds | Every seed tenant applies through the public API |
