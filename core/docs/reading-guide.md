# Reading the code like a senior engineer

A path through `core/api/` in the order that builds understanding fastest: contract and
rules first, then the spine of one request, then each engine from its purest file outwards,
then the tests that pin behaviour down. Each stop names the file, the question to answer
before moving on, and what to look for. About two hours with the code open; run
`python scripts/dev.py up` and `seed` first so you can poke at `http://localhost:8000/api/docs`
while reading.

Principle: **read the constraints before the code.** This codebase is shaped by a handful of
rules (one service call per request, `transition()` only, RLS, outbox). Once you hold them, most
files are predictable and you read them to confirm, not to discover.

## Stop 0: the constraints (15 min)

| Read | Question to answer |
| --- | --- |
| `../../CLAUDE.md` ("Rules for everyone") and `../../docs/backend.md` ("Rules") | What may a route do? What must a service do? Who may change status? |
| `../../docs/core-boundaries.md` | Why is there no `if product == …` anywhere, and what do you do instead? |
| `../../docs/api.md` ("Conventions", "Errors") | What does every response and every error look like? |
| `core/api/pyproject.toml` (`[tool.importlinter]`) | Which imports are forbidden? Find the two contracts. |

## Stop 1: the spine of a request (20 min)

Follow one `POST /bookings` with [request-lifecycle.md](request-lifecycle.md) beside you.

| File | Look for |
| --- | --- |
| `app/settings/base.py` | `ATOMIC_REQUESTS`, `MIDDLEWARE`, `REST_FRAMEWORK` (authentication class, exception handler). Everything downstream assumes these. |
| `app/urls.py` | How modules are mounted under `/api/v1/`; `healthz`. |
| `kernel/auth.py` | `AuthAdapter.verify()`: what a token must have. `JWTAuthentication.authenticate()`: how `sub` becomes a user without the kernel importing `modules.users` (`import_string`). |
| `kernel/access.py` | `TenantAPIView.initial()`: the exact order header → `SET LOCAL` → membership → `Access`. `require_perm()`: what a site-scoped permission means. |
| `kernel/errors.py` | The class per code; `problem_handler()`: how DRF's `ValidationError` becomes `errors[{field, message}]`. |
| `modules/booking/views.py` | `BookingListView.post`: count the lines; this is the whole pattern (permission, serializer, one call, response). |
| `kernel/idempotency.py` | Why the insert is in a savepoint; what differs between replay and conflict. |

Check yourself: without looking, say what status and `code` you get for a missing header, a
wrong tenant, a missing permission, a bad field, a taken slot.

## Stop 2: the lifecycle, the heart (20 min)

| File | Look for |
| --- | --- |
| `../../docs/domain/booking.md` ("The lifecycle") | The table of allowed moves. Keep it open. |
| `modules/booking/models.py` | `BookingStatus` (nine values, stored as-is), `BookingAllocation` (`effect`, `closed_at`): why allocations are rows, not a flag. |
| `modules/booking/lifecycle.py` | `MOVES` is the doc's table verbatim. Read `transition()` top to bottom: lookup → guards → status → effects → history → one event. Then `_effects()`: what each target status does to allocations and timers. `check_in_window()`, `cancel_deadline()`: policy values in seconds. |
| `modules/booking/migrations/0003_db_rules.py` | The generated `during` column and the exclusion constraint: the one line that makes double booking impossible. |
| `tests/test_lifecycle.py` | How 90 cases are generated from `MOVES`; the "every other move is 409" half. |

Check yourself: name the only function that writes `bookings.status`, and the three things it
always writes alongside.

## Stop 3: the pipeline (20 min)

| File | Look for |
| --- | --- |
| `../../docs/domain/booking.md` ("The pipeline") | The seven steps and "steps 1–6 only decide". |
| `modules/booking/service.py` | `BookingRequest`, `Evaluation`, `evaluate()`: find each step and the module it calls. `create_booking()`: where step 7 starts, the allocation insert and `SlotTaken`, `start_payment`, the `transition()` call and which move. `preview_booking()`: how little it adds. Then the actions (`approve` … `cancel`) and the payment side (`mark_paid`, `apply_payment_webhook`, `run_timer`). |
| `modules/booking/serializers.py` | `booking_json()`: where `history`, `appliedConfig` and `payment` come from. |
| `tests/test_bookings.py`, `tests/test_concurrency.py` | The race test: two threads, one slot, and the deadlock variant. |

## Stop 4: the engines the pipeline calls (30 min)

Read each from its pure file to its service.

| Engine | Pure file | Then | Question |
| --- | --- | --- | --- |
| Custom fields | `modules/config/fields.py` | `config/service.py: validate_values, add_fields, archive_field`; `config/models.py` | Why `pattern` instead of `format`? What does a record's `schema_id` point to and why does it never change? |
| Policies and versions | `modules/config/policy.py` | `config/service.py: publish_body`; `resources/service.py: update_flow_config, restore_policy_version` | Where does `STALE_VERSION` come from? Why is restore a new version? |
| Availability | `modules/availability/service.py: open_intervals, _subtract, free_slots` | `availability/search.py`; `availability/models.py` | Why are hours stored in local time while everything else is UTC? Why is `search.py` outside `service.py`? |
| Rules | `modules/rules/jsonlogic.py`, then `rules/engine.py` | `rules/service.py: check_rules, publish`; `docs/examples/rule.json` | How does "deny beats allow, specific scope wins" appear in `evaluate_rules()`? Where is the trace built? Why can a rule switch payment on but never off? |
| Payments | `modules/payments/service.py: quote, start_payment, record_webhook, refund_for` | `payments/views.py: PaymentWebhookView` | Why is the gateway message stored *before* it is checked? How does the tenant get set for a request with no JWT? |

## Stop 5: events, worker, timers (15 min)

| File | Look for |
| --- | --- |
| `../../docs/domain/events.md` | Why the outbox exists; "subscribers must cope with duplicates". |
| `modules/events/service.py` | `emit_event()` (in the caller's transaction), `subscribe`, `relay_batch()` (`SKIP LOCKED`, `processed_events`, retries). |
| `modules/events/consumers.py`, `modules/identity/consumers.py` | What a subscriber looks like; why the invitation e-mail is sent from here and not from the request. |
| `kernel/jobs.py`, `modules/booking/jobs.py` | `register_job`, `schedule_job`, `cancel_jobs`; each handler is a `transition()` as `SYSTEM`. |
| `worker/management/commands/run_worker.py` | `run_due_jobs()`: claim, `tenant_scope`, handler, done or retry. The loop. |
| `tests/test_worker.py`, `tests/test_flow_end.py` | "Delivered twice, processed once"; a no-show happening by itself. |

## Stop 6: tenancy and people (15 min)

| File | Look for |
| --- | --- |
| `kernel/db.py` | The SQL `enable_rls` emits, especially `NULLIF(...)` and `FORCE`; `same_tenant_fk`. |
| `infra/postgres/init.sql`, `tests/conftest.py: django_db_setup` | Why the role must not be superuser; how tests make sure of it. |
| `kernel/tenant_context.py` | `activate_tenant`, `tenant_scope`, `fresh_tenant_context`: the `ContextVar` and the bug it once had. |
| `modules/users/service.py` | `resolve_access()`: membership → grants; `user_from_claims()`: three ways a token maps to a user; `invite_member` → `accept_invitation`. `users/constants.py`: system roles from code. |
| `modules/users/migrations/0003_own_memberships.py` | The one RLS exception and when it applies. |
| `tests/test_auth_and_tenancy.py` | `test_a_request_leaves_no_tenant_behind`. |

## Stop 7: sign-in (10 min)

| File | Look for |
| --- | --- |
| `modules/identity/service.py` | `login()`: why it is not atomic and what it commits before raising. `refresh()`: family revocation on reuse. `issue_link` / `_use_link`: only hashes stored. `guest()`. |
| `modules/identity/views.py` | `_Public`: no authentication, `AllowAny`, throttle scope `auth`. |
| `modules/identity/urls.py` | Which two views are `non_atomic_requests` and why. |
| `tests/test_identity.py` | Which tests need `transaction=True` and why. |

## Stop 8: the edges (10 min)

| File | Look for |
| --- | --- |
| `app/docs.py` | What the hub serves and refuses (`_safe_file`); why Swagger gets a modified copy of the contract. |
| `modules/tenancy/management/commands/seed_demo.py` | Everything goes through the same service functions as the API; the people and the password. |
| `scripts/dev.py`, `infra/compose.yaml`, `infra/compose.dev.yaml`, `.env.example` | How configuration reaches each process; what the local override changes (source mount, reload). |
| `Dockerfile`, `pyproject.toml`, `uv.lock` | What the image contains and how dependencies are pinned. |
| `.gitlab-ci.yml` | Which commands CI runs; `python scripts/dev.py check` mirrors them. |

## When you are done

You should be able to answer, from memory: the four headers a client may send and when; the
order of checks on a request; the only writer of booking status and its three side effects;
why double booking is impossible and what the loser sees; how a change becomes an event and
how the worker delivers it once; why a missing tenant setting returns nothing instead of
everything; what a module may import from another module.

Then pick the engine your task touches, open its row in [engines.md](engines.md), and read
its test file first: the tests are the behaviour you must keep.
