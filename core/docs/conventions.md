# Conventions

The habits the code follows. Most come from `docs/backend.md` and `docs/api.md`; this page
says how they look in Django, and where the team's earlier Django style (`paihong_apis`) was
kept or changed.

## The module template

Every module is a Django app under `modules/` with the same files. Create a new one by
copying the shape, not by inventing a layout.

| File | Rule |
| --- | --- |
| `models.py` | Only this module's tables. Inherit `kernel.models.TenantModel` (or `BaseModel` for tenant-less tables). Status enums are `TextChoices` with string values. No business logic on models. |
| `service.py` | **The only file another module may import.** Keyword-only arguments, `@transaction.atomic` on anything that writes, raises `kernel.errors.*` on a broken rule. Reads are plain functions returning querysets (`*_qs`) or small frozen dataclasses (`*View`) for other modules. |
| `serializers.py` | Request shape only, camelCase field names exactly as the contract. `validate()` for cross-field shape checks, never for business rules. Response shaping is a function `thing_json(obj)` next to them, not a `ModelSerializer`, because responses are assembled from several tables and the contract's names differ from the columns. |
| `views.py` | One class per path, `TenantAPIView` (or `APIView` for public ones). A method does four things in order: `require_perm`, serializer, **one** service call, `Response`. No queries, no loops over models, no try/except for business errors (`problem_handler` does that). |
| `urls.py` | Kebab-case, plural nouns, no trailing slash (`APPEND_SLASH=False`), action endpoints as `POST /things/{id}/verb`. |
| `migrations/` | Generated `000N_initial.py`, then a hand-written `000N_db_rules.py` for RLS and composite keys in the same merge request. |
| `apps.py` | `ready()` imports side-effect modules (`jobs`, `consumers`) so handlers register. |
| engine files | Pure where possible (`rules/engine.py`, `rules/jsonlogic.py`, `config/fields.py`, `config/policy.py` take data in, return data out; no ORM, no clock). That is what makes them cheap to test exhaustively. |

Cross-module calls go `service → service`. If a module needs a query that combines several
modules' tables (free-slot search), the function lives outside `service.py`
(`availability/search.py`) and the import direction is chosen to avoid a cycle.

## How to add an endpoint

1. **Contract first.** Find or add the operation in `contracts/openapi.yaml` (the frontend
   owns its shape; propose changes in their merge request, do not edit alone). Note path,
   request, response and error codes.
2. **Tables.** If a table or column is missing: model, `makemigrations`, then the
   `_db_rules.py` migration with `enable_rls`, `same_tenant_fk`. Update
   [data-and-tenancy.md](data-and-tenancy.md).
3. **Service function** in the owning module's `service.py`: keyword-only arguments,
   `@transaction.atomic`, writes + `transition()` or `record_status()` + `emit_event()` in that
   order, raise `kernel.errors` subclasses. Add the event name to `docs/domain/events.md`
   if it is new.
4. **Serializer** for the request; `thing_json()` for the response.
5. **View method**: permission, serializer, one call, response. Status codes: 201 for creates,
   200 for actions and reads, 204 for deletes, 202 for accepted-and-silent (`forgot`).
6. **URL** in the module's `urls.py`.
7. **Tests** in `tests/`: the happy path over HTTP; each error code the contract lists; the
   tenant-isolation case (tenant B cannot see or do it); for an action, one wrong-state move
   → 409. Use the fixtures of `conftest.py`.
8. **Run** `python scripts/dev.py check`. Then add the endpoint to the Postman scenario in the
   notes folder (`docs/postman/scenario_*.py`, rebuild with `build_collection.py`) so it is
   covered by the contract-schema checks, and regenerate [api-table-map.md](api-table-map.md).
9. **Docs**: the engine row in [engines.md](engines.md) if a guarantee changed;
   [open-decisions.md](open-decisions.md) if you chose something the shared docs do not say.

## Errors

| Situation | Raise | Becomes |
| --- | --- | --- |
| Bad input shape | DRF serializer error, or `ValidationFailed.one(field, message)` / `ValidationFailed(errors=[…])` | `422 VALIDATION_FAILED`, `errors[{field, message}]` |
| A policy or rule says no | `BookingDenied(reasons=[{ruleId, message}])` | `422 BOOKING_DENIED` |
| The slot is taken | `SlotTaken` | `409 SLOT_TAKEN` |
| Move not in the lifecycle table, or wrong current state | `InvalidTransition` | `409 INVALID_TRANSITION` |
| Edit on an old version | `StaleVersion` | `409 STALE_VERSION` |
| Not signed in / bad token | `Unauthenticated` | `401 UNAUTHENTICATED` |
| Not a member, no permission | `Forbidden` | `403 FORBIDDEN` |
| Not found in this tenant | `NotFound` | `404 NOT_FOUND` (never 403: do not reveal other tenants' ids) |

Messages are for humans and may change; `code` and `errors[].field` are the contract. Never
return `{status, data, message}` wrappers: the frontend's client is generated from the
contract and expects the bare object.

## Transactions and side effects

- A request is one transaction (`ATOMIC_REQUESTS`). Do not open nested `transaction.atomic()`
  for business reasons; use a savepoint only to survive an expected integrity error
  (`idempotency.py`, the allocation insert).
- Anything that must happen *after* commit (sending an e-mail, calling a gateway) is either an
  outbox event handled by the worker, or `transaction.on_commit()` for the rare case where the
  request itself must send it (`identity.forgot_password`).
- Never call another system inside the transaction.
- The two `non_atomic_requests` views (`/auth/login`, `/auth/refresh`) are the documented
  exception; do not add a third without a note in [open-decisions.md](open-decisions.md).

## Time

- Store UTC (`timestamptz`), accept and return ISO 8601 with an offset
  (`kernel.serializers.AwareDateTimeField` rejects naive timestamps).
- Opening hours and "the date D at site S" are local: convert with the site's `ZoneInfo`
  per day (`availability/service.py: _local`, `day_bounds`). Never add a fixed +7.
- `django.utils.timezone.now()` everywhere; tests freeze or compute relative times.

## Tests

- Written with the code, in the same merge request; the engine table says which file.
- Over HTTP through `APIClient` when the behaviour is visible to a client; direct service
  calls for engine internals (`test_lifecycle.py`, `test_rules_engine.py`).
- Real PostgreSQL always (`pytest-django`); no SQLite, no mocking the database: RLS, the
  exclusion constraint and `SKIP LOCKED` are the point.
- `@pytest.mark.django_db(transaction=True)` only when the code under test commits on purpose
  (login, refresh) or needs two connections (concurrency).
- Fixtures build worlds, tests state facts. A test name says the fact
  (`test_reusing_a_refresh_token_ends_the_session`).

## Lint and format

`ruff` with the rule sets in `pyproject.toml` (pyflakes, pycodestyle, isort, bugbear,
pyupgrade, Django, bandit, simplify, ruff). Line length 100. `ruff format`. Per-file
exceptions are listed with their reason. `lint-imports` enforces the two contracts
(modules only through `service.py`; kernel imports nothing above it). `python scripts/dev.py
check` runs all of it the way CI does.

## Naming

- Python: `snake_case`; tables plural `snake_case`; JSON `camelCase` (contract);
  URL paths `kebab-case`.
- Service functions are verbs (`create_booking`, `publish_policy`, `set_member_roles`); read
  helpers end in `_qs` (queryset) or start with `get_`/`list_`/`describe`.
- Event names are past-tense facts, `object.verb` (`booking.confirmed`, `member.invited`).
- Job types are upper snake (`MARK_NO_SHOW`); permission codes are `object.verb` lower
  (`booking.check_in`).
- Error codes are upper snake and live in the contract.

## Kept from `paihong_apis`, and changed

| Kept | Changed, and why |
| --- | --- |
| Thin views; serializers validate shape; services hold the rules with keyword-only arguments and `@transaction.atomic`; one named migration per change | One `models.py` per module instead of one for the project (import-linter, ownership) |
| `seed_*` style management commands (`seed_demo`, `create_tenant`) | Responses are the bare contract object, not `{status, data, message}` |
| Settings in `app/`, a `.env` file for local configuration | `422` with per-field errors and stable codes instead of `400` with one message |
| | UUIDv7 ids, cursor pagination, string enums, `USE_TZ=True`: all required by the contract |
| | Permission per tenant and site (`require_perm(access, code, site_id)`) instead of a global role |
| | History and events written in the same transaction, not fire-and-forget |
| | One worker on PostgreSQL instead of Celery, APScheduler and Redis |
| Code mounted into the containers with auto-reload, for local work (`infra/compose.dev.yaml`) | `ruff` instead of black, isort and flake8 |
| A lock file and `pyproject.toml` (uv here, Poetry there) | uv instead of Poetry: same `pyproject.toml` standard (PEP 621), much faster installs in Docker and CI |
