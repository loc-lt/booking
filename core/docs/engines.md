# The engines

The backend is a small number of guarantees, each with one place in the code and one test
file that proves it. When you change code, find the engine you are inside and keep its
guarantee; when you add a feature, decide which engine it belongs to before writing.

| Engine | Lives in | Guarantees | Proven by |
| --- | --- | --- | --- |
| **Tenancy** | `kernel/access.py`, `kernel/tenant_context.py`, `kernel/db.py`, every `*/migrations/*_db_rules.py` | Every tenant table is filtered by row-level security, forced, with the tenant set per request or per job; composite foreign keys keep every reference inside one tenant; no membership → 403; the tenant context cannot leak between requests | `test_auth_and_tenancy.py` |
| **Sign-in** (D-003) | `modules/identity/` | Email + password with PBKDF2 and Django's validators; 15-minute access tokens; refresh tokens that work once and end the whole session when reused; lockout after 5 wrong passwords; the same 401 for unknown e-mail and wrong password; one-time links stored hashed; guest tokens without refresh; e-mails sent after commit | `test_identity.py` |
| **People and access** | `modules/users/` | Roles are sets of permission codes, optionally per site; the five system roles follow the code and cannot be edited; invitations are claimed only by the invited e-mail (link, or a verified external token); disabling a member cuts access at once | `test_people.py` |
| **Config versions** | `modules/config/service.py`, `modules/resources/service.py` | Policies are immutable versions; an edit on a stale `baseVersion` is `STALE_VERSION`; a booking keeps the version it was made under; restore republishes an old body as the newest version; a no-op edit publishes nothing; every publish emits `config.published` | `test_resource_types.py`, `test_config_flex.py` |
| **Custom fields** | `modules/config/fields.py` | Field definitions compile to JSON Schema that the browser (Ajv) and the server check identically (patterns, not formats); fields can be added or archived later without rewriting records; keys are permanent; values are checked against the form version the record points to | `test_resource_types.py`, `test_config_flex.py` |
| **Availability** | `modules/availability/` | Hours in the site's local time compared in UTC, daylight-saving safe; a resource may override its site's hours; blocked and extra-open ranges; buffers before and after; the free-slot search combines hours, exceptions, open allocations and resource status | `test_availability.py`, `test_sites_and_resources.py` |
| **Pipeline** | `modules/booking/service.py: evaluate, create_booking, preview_booking` | The seven steps run in a fixed order; steps 1–6 decide only (so preview is free of side effects); every denial names the setting or rule in `reasons[]` | `test_bookings.py`, `test_rules_api.py` |
| **Rules** | `modules/rules/` | Rule sets are immutable versions checked at publish; conditions are a JSONLogic subset over a fixed context; deny beats allow; the more specific scope wins; quotas count real usage; every decision carries a trace; a booking records the rule set version that judged it | `test_rules_engine.py`, `test_rules_api.py` |
| **No double booking** | `modules/booking/migrations/0003_db_rules.py`, `kernel/db.py` | PostgreSQL's exclusion constraint on open allocations makes a race impossible; the loser gets `409 SLOT_TAKEN`, including when the two transactions deadlock | `test_concurrency.py` |
| **Lifecycle** | `modules/booking/lifecycle.py: transition` | The only code that changes a booking's status; moves outside the table are `409 INVALID_TRANSITION`; each move runs its guards and effects, writes exactly one history row and emits exactly one event, all in the caller's transaction | `test_lifecycle.py` (90 cases), `test_flow_end.py` |
| **Payments** | `modules/payments/service.py`, the payment side of `modules/booking/service.py` | An up-front policy holds the slot until paid; the desk (`mark-paid`) or a signed gateway webhook pays exactly once (duplicates and forged signatures are recorded and ignored); an unpaid hold expires; refunds follow the policy's rules; late or unmatched money goes to a reconciliation queue | `test_payments.py` |
| **Outbox and worker** | `modules/events/service.py`, `worker/` | An event is saved in the same transaction as the change; the worker delivers it at least once and each subscriber processes it at most once; failures retry with growing delays, then park | `test_worker.py` |
| **Timers** | `kernel/jobs.py`, `modules/booking/jobs.py` | No-show, auto-complete, approval timeout and hold expiry are scheduled inside the transaction that needs them and cancelled when the booking moves on; every timer acts through `transition()` as `SYSTEM` | `test_worker.py`, `test_payments.py`, `test_flow_end.py` |

## How they connect

```text
                 ┌──────────── Sign-in ────────────┐
   token ───────►│ verify, map to user             │
                 └───────────────┬─────────────────┘
                 ┌───────────────▼─────────────────┐
   X-Tenant-Id ─►│ Tenancy: SET LOCAL, membership  │──► People and access: permission?
                 └───────────────┬─────────────────┘
                                 ▼
   POST /bookings ──► Pipeline ──┬─► Custom fields   (step 1)
                                 ├─► Availability    (step 2)
                                 ├─► Rules           (steps 3–5)
                                 ├─► Payments: quote (step 6)
                                 └─► step 7: allocation ──► No double booking
                                              booking
                                              Lifecycle.transition() ──► history row
                                                                    ├──► Outbox event
                                                                    └──► Timers scheduled
   later: Worker ──► delivers events to subscribers (e-mail, audit, …)
                 └─► runs due timers ──► Lifecycle.transition() as SYSTEM
```

Config versions sit underneath: the pipeline reads the policy version current at booking time
and the booking stores it, so a later edit never changes an existing booking's rules.

## What is deliberately not an engine (yet)

- **Pricing** beyond a flat amount per booking or per hour: `payments.service.quote()` reads
  the policy; price plans, credits and discounts are a later engine (`docs/product.md`, axis 5).
- **Notifications**: the worker has an `audit_log` subscriber and the invitation mailer. A
  template-per-event-and-channel engine is listed in `docs/architecture.md` and not built.
- **Outbound webhooks** to products, with signatures and retries: planned before the first
  product (`docs/architecture.md`, "Before the first product starts").
- **Service tokens** with scopes for product backends: same.
