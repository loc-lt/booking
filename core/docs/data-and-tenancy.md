# Data and tenancy

Twenty-eight tables in one PostgreSQL database, each owned by exactly one Django app. The
design is the 24-table MVP of the team's database document (`../../../docs/database/`, with
`booking_core_mvp.dbml`), plus four tables added while building: `rule_set_versions` and the
three sign-in tables. Measured reads and writes per endpoint: [api-table-map.md](api-table-map.md).

## Tables by owner

| Module | Table | Holds | RLS |
| --- | --- | --- | --- |
| tenancy | `tenants` | One customer organisation: slug, name, timezone, currency, `settings` JSONB (e.g. `guestBooking`) | no (the root) |
| users | `users` | A person across tenants: `auth_subject` (`<issuer>|<sub>`), e-mail (nullable: guests), name | no (not tenant-scoped) |
| users | `memberships` | A person in a tenant: status INVITED / ACTIVE / DISABLED, display name, default site | yes, plus `own_memberships` (read your own while no tenant is active, for `/me/tenants`) |
| users | `roles`, `role_permissions`, `membership_roles` | Roles per tenant (5 system roles plus tenant-made ones), their permission codes, who has which role, optionally at one site | yes |
| identity | `user_credentials` | PBKDF2 password hash, failed attempts, `locked_until` | no (per user) |
| identity | `refresh_tokens` | SHA-256 of each refresh token, its family, what replaced it, when revoked | no |
| identity | `auth_tokens` | SHA-256 of one-time links (password reset, invitation), purpose, expiry, used-at | no |
| resources | `locations` | A site: code, name, timezone, address, status | yes |
| resources | `resource_types` | A template: code, name, slot minutes, booking mode, `current_policy_version` | yes |
| resources | `resources` | One bookable thing: type, site, name, code, status, `attributes` JSONB, `schema` (the form version its values were checked against) | yes |
| config | `policy_versions` | Immutable published policy bodies per type, version n, `based_on_version` | yes |
| config | `field_definitions` | Custom field definitions: object, type, key, label JSONB, scope, validation, status | yes |
| config | `object_schema_versions` | The compiled JSON Schema of one object's fields at one version | yes |
| availability | `availability_rules` | Weekly opening hours of a site or a resource, in local time | yes |
| availability | `availability_exceptions` | A blocked or extra-open range on a site or resource, with reason | yes |
| booking | `bookings` | The claim: resource, booker, `start_at`/`end_at`, status (nine contract values), `attributes`, `policy_version`, rule set version, channel, public code | yes |
| booking | `booking_allocations` | The time range a booking holds on a resource: effect HOLD/LOCK, `during` (generated range), `closed_at` | yes |
| payments | `payments` | One payment per booking: amount minor units, status, gateway session, refunded amount | yes |
| payments | `payment_events` | Every gateway message received, stored before it is checked: gateway, event id, outcome (applied, duplicate, ignored, needs reconciliation) | yes |
| payments | `refunds` | A refund request: amount, applied rule, status | yes |
| rules | `rule_set_versions` | Immutable snapshot of the whole rule set at version n, with note and publisher | yes |
| events | `outbox` | Events waiting for delivery: name, tenant, subject, actor, changes, versions, attempts | no (worker scans all tenants) |
| events | `processed_events` | `(consumer, event_id)` already handled | no |
| kernel | `transition_log` | One row per status move of any object: object code, record, action, from, to, actor kind and membership, reason, request id | yes |
| kernel | `scheduled_jobs` | Timers: job type, record, `run_at`, status, attempts, `locked_until` | no (worker scans all tenants) |
| kernel | `idempotency_keys` | Key, endpoint, request hash, stored response, expiry | yes |

Two tables are written by no endpoint, by design: `tenants` only by platform commands
(`create_tenant`, `seed_demo`), `processed_events` only by the worker.

## Row-level security

The core's isolation does not depend on remembering a `WHERE tenant_id = …`.

1. `infra/postgres/init.sql` creates the application role `booking_app` with `NOSUPERUSER
   NOBYPASSRLS`. Superusers and `BYPASSRLS` roles skip policies even when forced, so the
   application must never connect as one. Tests switch to such a role when they find
   themselves superuser (CI's service container), otherwise the tenancy tests would pass for
   the wrong reason.
2. Every tenant table's `000N_db_rules.py` migration calls `kernel.db.enable_rls(table)`, which
   emits `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY` (so even the table owner is
   filtered) and one policy: `tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid`.
   No setting → the expression is NULL → no row is visible. Missing context returns nothing
   rather than everything.
3. `kernel/access.py` runs `SET LOCAL app.tenant_id = '<uuid>'` after the membership check;
   `SET LOCAL` lives for the transaction, which is the request (`ATOMIC_REQUESTS=True`). The
   worker does the same per job through `kernel.tenant_context.tenant_scope()`.
4. `users/migrations/0003_own_memberships.py` adds the one exception: a SELECT-only policy on
   `memberships` for `user_id = app.user_id` while `app.tenant_id` is empty, so `GET /me/tenants`
   can list a person's tenants before a tenant is chosen.

A regression test (`test_auth_and_tenancy.py: test_a_request_leaves_no_tenant_behind`) guards
the one bug this design had: the tenant `ContextVar` leaking from one request to the next on
the same thread. `RequestIdMiddleware` now resets it per request.

## Same-tenant foreign keys

A row must never reference a row of another tenant, even through a bug in application code.
`kernel.db.same_tenant_fk(table, column, target)` adds a composite foreign key
`(tenant_id, <column>) REFERENCES <target>(tenant_id, id)`, which needs a matching unique
`(tenant_id, id)` on the target (also emitted). Every `000N_db_rules.py` of a module with
cross-table references uses it: a booking's resource, a resource's type and site, a
membership role's role, and so on.

## Database-level business rules

| Rule | Where | Error surfaced as |
| --- | --- | --- |
| No two open allocations overlap on one resource | `booking/migrations/0003_db_rules.py`: generated `during tstzrange` column, `CHECK (end_at > start_at)`, `EXCLUDE USING gist (tenant_id WITH =, resource_id WITH =, during WITH &&) WHERE (closed_at IS NULL)` | `409 SLOT_TAKEN` (`kernel.db.violated_constraint` names the constraint) |
| `attributes` is a JSON object | `kernel.db.attributes_check()` on `resources`, `bookings`, `memberships` | 500 (should never happen: the service validates first) |
| One gateway message once | unique `(gateway, gateway_event_id)` on `payment_events` | outcome `duplicate` |
| One refresh token hash | unique `token_hash` on `refresh_tokens` | — |

## Conventions

- **IDs** are UUIDv7 (`kernel/uuid7.py`): time-ordered, so indexes stay compact and ids sort by
  creation.
- **Time** is `timestamptz`, stored in UTC (`USE_TZ=True`). Opening hours are the exception:
  `availability_rules` keeps local wall-clock times with the site's timezone, because "open
  07:00–21:00" must survive daylight-saving changes; comparisons convert to UTC per day.
- **Statuses** are the contract's strings (`confirmed`, `awaiting_payment`, …) in `bookings`,
  and upper-case codes in the older tables (`ACTIVE`, `PENDING`, `PAID`). Only the booking ones
  are visible as-is through the API; the others are mapped in the serializers.
- **JSONB** columns (`attributes`, `settings`, `body`, `label`, `changes`) are the flexibility
  of the product: a tenant adds a custom field without a schema change. Their shape is checked
  in Python (`config/fields.py`, `config/policy.py`) against the version the row points to.
- **Nullable text** means "not set", distinct from `""` (ruff rule DJ001 is disabled for that
  reason).

## Migrations

| File | Holds |
| --- | --- |
| `0001_initial.py` (and `0002_initial.py` where a second pass was needed) | Generated by `makemigrations`: tables, plain columns, Django-level indexes |
| `000N_db_rules.py` | Hand-written `RunSQL` through `kernel/db.py`: RLS, composite foreign keys, CHECKs, the exclusion constraint, extra indexes |
| Named migrations, e.g. `payments/0003_payment_events_refunds.py`, `users/0003_own_memberships.py` | A later feature, named after what it adds |

Rules: migrations run as a separate step (`migrate` container, `deploy_demo` job), never at
app start; a change must be backward compatible for one release (add, deploy, remove later);
a table with `tenant_id` gets its RLS and composite keys in the same merge request that
creates it. The foreign-key cycle `memberships → locations → memberships` is why `users`
has a second migration adding `default_location_id` after `resources` exists.

## Looking at the data

```bash
python scripts/dev.py psql                       # as booking_app: RLS applies, you see nothing until
# SET app.tenant_id = '<tenantId>';              # …you set the tenant for the session
python scripts/dev.py manage shell               # Django shell inside the container
python scripts/dev.py timers <tenantId>          # make pending timers due, then watch `logs worker`
```
