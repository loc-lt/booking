# One request, end to end

What happens between a client sending `POST /api/v1/bookings` and the response, and what the
worker does afterwards. Read it with [structure.md](structure.md) open; every step names its
file.

## The three kinds of endpoints

| Kind | Endpoints | Must carry | Base view |
| --- | --- | --- | --- |
| Public | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/password/forgot`, `/auth/password/reset`, `/auth/invitations/accept`, `/auth/guest` | nothing; throttled per client address (`AUTH_RATE`) | `identity/views.py: _Public` |
| Gateway | `/webhooks/payments/{gateway}/tenants/{tenantId}` | `X-Signature` (HMAC-SHA256 of the raw body); the tenant is in the URL because payments sit behind RLS and the gateway has no JWT | `payments/views.py: PaymentWebhookView` |
| Signed in, no tenant | `/auth/password/change`, `/me/tenants` | `Authorization: Bearer <access token>` | DRF `APIView` with `JWTAuthentication` |
| In a tenant | everything else | `Authorization` and `X-Tenant-Id`; `Idempotency-Key` on `POST /bookings` | `kernel/access.py: TenantAPIView` |

## Step by step: `POST /bookings`

```text
client ──► Caddy (/api/*) ──► gunicorn (app.wsgi) ──► Django middleware ──► DRF view ──► service ──► PostgreSQL
```

1. **Middleware** (`app/settings/base.py: MIDDLEWARE`).
   `LocalCorsMiddleware` answers the browser's preflight locally. `RequestIdMiddleware`
   reuses `X-Request-ID` or makes one, binds it to the log context, and resets the tenant
   `ContextVar` so nothing from the previous request on this thread survives. Django opens the
   request transaction here (`ATOMIC_REQUESTS=True`).

2. **Authentication** (`kernel/auth.py: JWTAuthentication`).
   `AuthAdapter.verify()` checks signature, `exp`, `iss`, `aud` (HS256 with `JWT_SECRET`, or a
   JWKS). `modules.users.service.user_from_claims()` maps `iss|sub` to a `users` row (tokens
   the core issued always point at an existing user; a token from another issuer may create
   one on first sight or claim a pending invitation when the e-mail is verified).
   `activate_user()` runs `SET LOCAL app.user_id`. Failure → `401 UNAUTHENTICATED`.

3. **Tenant and permissions** (`kernel/access.py: TenantAPIView.initial`).
   `parse_tenant_header()` requires a UUID in `X-Tenant-Id` (else `422 VALIDATION_FAILED`,
   field `X-Tenant-Id`). `activate_tenant()` runs `SET LOCAL app.tenant_id`; from now on every
   query on a tenant table is filtered by row-level security. `modules.users.service.resolve_access()`
   loads the caller's ACTIVE membership in that tenant and its grants (role → permission codes,
   optionally per site) into `request.access`. No membership → `403 FORBIDDEN`.

4. **View** (`modules/booking/views.py: BookingListView.post`).
   `require_perm(request.access, perms.BOOKING_CREATE)` (403 if missing).
   `CreateBookingRequest(data=request.data).is_valid(raise_exception=True)`: shape only, with the
   contract's camelCase names; DRF errors become `422 VALIDATION_FAILED` with per-field
   `errors[]` through `problem_handler`. Then `run_idempotent()` wraps the one service call.

5. **Idempotency** (`kernel/idempotency.py`).
   The key is stored with a hash of endpoint and body in a savepoint. Same key and same hash
   → the stored response is returned without running anything; same key and a different body
   → 422 on field `Idempotency-Key`; missing key → 422.

6. **Service: the pipeline** (`modules/booking/service.py: create_booking → evaluate`).
   The seven steps of `docs/domain/booking.md`, each a call into another module's `service.py`:

   | Step | Calls | Denies with |
   | --- | --- | --- |
   | 1 validate request | `config.service.validate_values()` (JSON Schema compiled from the type's booking-scoped fields); slot alignment; resource status | `422 VALIDATION_FAILED` per field, or `BOOKING_DENIED resource.status` |
   | 2 availability | `availability.service.is_open()` (site or resource hours in local time, exceptions), buffers | `BOOKING_DENIED availability.hours` |
   | 3–5 rules and limits | `rules.service.decide()`: every enabled rule in scope, one pass, with the fixed context (`booking`, `resource`, `user`, `user.roles`, `time`, `usage`), plus the policy's own limits. `require_approval` and `require_payment` matches switch approval or payment on | `BOOKING_DENIED` with the rule ids in `reasons[]` |
   | 6 price | `payments.service.quote()` from the policy (also when a `require_payment` rule matched) | — |
   | 7 save | below | `409 SLOT_TAKEN` |

   Steps 1–6 write nothing, which is why `POST /bookings/preview` can run them as a dry run.

7. **Service: step 7, in the same transaction.**
   Insert the `booking_allocations` row first (HOLD or LOCK). PostgreSQL's exclusion constraint
   on `(tenant_id, resource_id, during)` for open allocations rejects the second of two racing
   requests; `kernel/db.py: violated_constraint()` recognises it and the service raises
   `SlotTaken`. Then insert `bookings`, call `payments.service.start_payment()` when the policy
   charges up front, and run `lifecycle.transition(booking, "confirm" | "require_approval" |
   "require_payment", actor)`.

8. **`transition()`** (`modules/booking/lifecycle.py`).
   Looks the move up in `MOVES` (else `409 INVALID_TRANSITION`), runs the guards, sets the
   status and its timestamp, runs the effects of the new status (allocation HOLD → LOCK or
   close; schedule or cancel `scheduled_jobs` such as `MARK_NO_SHOW`, `AUTO_COMPLETE`,
   `APPROVAL_TIMEOUT`, `EXPIRE_HOLD`), inserts one `transition_log` row with the request id,
   and calls `events.service.emit_event()` once: one `outbox` row in the same transaction.

9. **Response.** `booking_json()` shapes the contract's `Booking` (`status`, `history` from
   `transition_log`, `appliedConfig` from the policy version the booking stored, `payment`).
   The idempotency row is updated with the response. Django commits; `SET LOCAL` values vanish
   with the transaction. `X-Request-ID` is echoed.

10. **Any failure** anywhere raises; Django rolls the transaction back, so there is never a
    booking without its allocation, history and event. `problem_handler()` renders
    `application/problem+json` with `type`, `title`, `status`, `code`, `detail`, and `errors[]`
    or `reasons[]`. Two deliberate exceptions: `/auth/login` and `/auth/refresh` are
    `non_atomic_requests` views that commit the failed-login counter and the revocation of a
    reused refresh token before answering 401.

## After the response: the worker

`worker/management/commands/run_worker.py` loops every `WORKER_POLL_SECONDS`:

1. **Outbox delivery** (`modules/events/service.py: relay_batch`). Claims undelivered `outbox`
   rows with `FOR UPDATE SKIP LOCKED`. For each subscriber of the event's name
   (`events/consumers.py`, `identity/consumers.py`, registered with `@subscribe`): skip when a
   `processed_events` row exists, else run the handler inside `tenant_scope(event.tenant_id)`
   and insert the `processed_events` row. Failures increase `attempts` and push
   `available_at` back; after `WORKER_MAX_ATTEMPTS` the event is parked.

2. **Timers** (`run_due_jobs`). Claims `scheduled_jobs` with `status = PENDING` and `run_at <= now()`,
   marks them RUNNING, and runs the handler registered for the job type
   (`modules/booking/jobs.py`) inside `tenant_scope(job.tenant_id)`. Every handler goes through
   `transition()` as `SYSTEM`, so a timer can never do what the API cannot. Done → `DONE`;
   error → retry later.

The worker scans across tenants, so `outbox`, `processed_events` and `scheduled_jobs` have no
row-level security; only code writes them, and `GET /events` filters by tenant explicitly
([open-decisions.md](open-decisions.md), item 5).

## The same shape everywhere

Every other write endpoint follows steps 1–4 and then **one** service function in one
transaction that writes its rows, a `transition_log` row when a status changed (bookings
through `transition()`, everything else through `kernel/history.py: record_status()`), and an
`outbox` row through `emit_event()`. Read endpoints stop after step 4 and call a `*_qs()` or
`get_*()` function plus `kernel/pagination.py: paginate()`.
