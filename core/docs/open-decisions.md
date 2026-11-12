# Open decisions

Choices the code makes that the shared docs do not yet record, or contradict. Each needs the
owner named in the root `CLAUDE.md` ("Who approves doc changes"); until then the code is the
proposal and this page is its record. When one is approved: update the shared doc, add the
`docs/decisions.md` entry, and remove the row here.

| # | Decision in the code | Changes which shared doc | Approver |
| --- | --- | --- | --- |
| 1 | **D-002: Django + DRF instead of Flask + SQLAlchemy + Alembic.** Migrations are Django's, run by the `migrate` container and the deploy job (`python manage.py migrate`). | `docs/backend.md` ("Structure", "Libraries", table list), `docs/architecture.md` ("Stack") | Lead + one backend engineer; CI already adapted |
| 2 | **The database stores the contract's nine booking statuses** (`confirmed`, `awaiting_payment`, …), not the seven of `booking_core_mvp.dbml`; `create_target` was dropped from the policy body. | Team database doc (notes folder); `docs/backend.md` table list | Backend engineers |
| 3 | **Policy body keys** `cancel_allowed_until_seconds` and the contract's `flowConfig.limits`, `buffers`, `payment` sections (`price` → `{amount_minor, per}`, `refund_rules` → `[{before_seconds, percent}]`). | `docs/domain/configuration.md`, `docs/examples/flow-config.json`, `payment-policy.json` | Lead + frontend + backend |
| 4 | **A confirmed booking whose policy needs no check-in completes at its end** (`AUTO_COMPLETE`, move `confirmed → completed`, timer only). | `docs/domain/booking.md` ("Allowed moves") | Lead |
| 5 | **No RLS on `scheduled_jobs`, `outbox`, `processed_events`**: the worker scans across tenants and runs each item inside its tenant; only code writes them; `GET /events` filters by tenant explicitly. | `docs/backend.md` ("Data and tenancy") | Backend engineers |
| 6 | **`users.email` is nullable** (guests may give none). Invitations create a placeholder user (`auth_subject = invite|<email>`) that the emailed link or a verified external token claims. | `docs/backend.md` ("Auth") | Backend engineers |
| 7 | **Members' cancellation deadline does not bind staff** (`booking.cancel_any`); staff cancellations refund 100%. | `docs/domain/booking.md` | Lead |
| 8 | **Rules are stored as immutable snapshots in `rule_set_versions`** (one table outside the 24), no drafts. | `docs/domain/rules.md`, `docs/domain/configuration.md` ("Draft") | Lead |
| 9 | **System roles take their permissions from code** (`users/constants.py`), not from `role_permissions`, and cannot be edited through the API. | `docs/backend.md` ("Auth", roles) | Backend engineers |
| 10 | **New events**: `member.invited|joined|disabled|enabled|roles_changed`, `payment.session_created|paid|failed|expired|reconciliation_needed`, `refund.requested|succeeded`; resource status changes use `resource.updated`. | `docs/domain/events.md` ("Event catalogue") | Lead |
| 11 | **Webhook path `/webhooks/payments/{gateway}/tenants/{tenantId}`**: the one place the tenant comes from the URL; mock gateway only, HMAC-SHA256 with `PAYMENT_WEBHOOK_SECRET`. | `docs/api.md` ("Tenant: never from URL" needs the exception), `docs/domain/booking.md` ("Payment") | Lead + frontend + backend |
| 12 | **The contract grew from 16 to 69 operations**, additively. Needs the frontend's `pnpm gen` and one frontend + one backend + lead approval per `docs/api.md`. | `contracts/openapi.yaml` (done), generated client (frontend) | Lead + both roles |
| 13 | **D-003: the core signs people in** (`modules/identity`, `/auth/*`, three tables without RLS). Proposed in `docs/decisions.md`; `docs/backend.md` "Auth" already rewritten. HS256 now; RS256 + JWKS before products verify tokens themselves. | `docs/architecture.md` ("Auth" row, "How products use the core"), `docs/operations.md` ("Outside services"), `docs/glossary.md` ("Guest") | Lead |
| 14 | **Two non-atomic views** (`/auth/login`, `/auth/refresh`) commit before answering 401, so the failed-login counter and the revocation of a reused token survive. | `docs/backend.md` ("Rules": one transaction per request) | Backend engineers |
| 15 | **Refunds are recorded by whoever has `payment.refund`**; the `staff` system role has `payment.mark_paid` but not `payment.refund`, so the desk cannot settle a cash refund. Either give `staff` the permission or keep it for owners/admins. | `docs/backend.md` (roles), `users/constants.py` | Backend engineers, product owner |

## Not decisions, but known gaps

- `docs/backend.md` "Contract checks: Schemathesis" and the CI job `api_contract_and_seeds`
  are stubs; the Postman scenario in the notes folder does the contract-schema checking today.
- `seeds/` (demo tenants as configuration applied through the API) is still empty; `seed_demo`
  creates demo data through service functions instead.
- Outbound webhooks, service tokens, a notifications engine and real pricing are listed in
  `docs/architecture.md` as "before the first product" and are not built
  ([engines.md](engines.md), "What is deliberately not an engine").
- Three lifecycle moves the code allows have no scenario step yet: `awaiting_payment →
  pending_approval`, and `cancel` from `awaiting_payment` and from `pending_approval`
  (`test_lifecycle.py` covers them; the Postman scenario does not).
