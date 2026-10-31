# Booking Core

This repo is the **booking core**: a configurable booking engine, shared frontend packages, two reference apps that demonstrate and test it, and seed data. Products such as co-working and workplace management live in their own repos and use the core through its API, webhooks and published packages.

These docs are the single source of truth. If code and docs disagree, the docs win until a reviewed merge request fixes one of them.

## Where to find things

| Doc | Covers | Read it when you work on |
| --- | --- | --- |
| [docs/product.md](docs/product.md) | Why the core exists, what customers configure | Anything, once |
| [docs/demo-plan.md](docs/demo-plan.md) | December demo: story, scope, team, timeline | Planning |
| [docs/glossary.md](docs/glossary.md) | Shared terms | Anything |
| [docs/architecture.md](docs/architecture.md) | Stack, repo layout, modules, how products use the core | Anything, once |
| [docs/core-boundaries.md](docs/core-boundaries.md) | Keeping product logic out of the core | Anything |
| [docs/domain/booking.md](docs/domain/booking.md) | Pipeline, lifecycle, policies, payment | Booking features |
| [docs/domain/rules.md](docs/domain/rules.md) | Rule model and evaluation | Rules |
| [docs/domain/configuration.md](docs/domain/configuration.md) | Versioned config, custom fields, type changes | Settings, custom fields |
| [docs/domain/events.md](docs/domain/events.md) | Events and the outbox | Anything that reacts to changes |
| [docs/api.md](docs/api.md) | API conventions, errors, contract workflow | Any endpoint |
| [docs/frontend.md](docs/frontend.md) | Frontend stack, code rules, mocks, testing | `web/apps/`, `web/packages/` |
| [docs/backend.md](docs/backend.md) | Backend structure, data, tenancy, auth, engine, testing | `core/` |
| [docs/analytics.md](docs/analytics.md) | What we measure, tracking plan | Screens and tracked events |
| [docs/operations.md](docs/operations.md) | Environments, Docker, CI/CD, deploys, secrets | `infra/`, `.gitlab-ci.yml` |
| [docs/decisions.md](docs/decisions.md) | Decision log | Before changing a convention |
| [docs/examples/](docs/examples/) | Example payloads, SQL, product setup | When a doc points there |

Folder-level `CLAUDE.md` files load the right guide automatically: `web/apps/` and `web/packages/` load the frontend guide, `core/` the backend guide, `contracts/` the API guide, `infra/` the operations guide.

## Rules for everyone, including agents

### Before starting

1. Read the docs for the area you're touching.
2. If the task needs a decision the docs don't cover, stop and ask. Don't invent a convention.
3. If the task conflicts with the docs, say so before writing code.

### While working

- Stay in scope. No drive-by refactors, renames or formatting in unrelated files.
- Never edit generated code in `web/packages/api-client/src/generated/`. Change `contracts/openapi.yaml` and run `pnpm gen`.
- Every new or changed endpoint, field or error code starts in the contract ([docs/api.md](docs/api.md)).
- No product-specific code anywhere ([docs/core-boundaries.md](docs/core-boundaries.md)).
- Apps use packages only through their entry points, and the core only through its public API.
- No new dependencies without asking: name the package, why it's needed, and the alternative considered.
- No secrets in code, tests, fixtures, commits or logs.
- Booking status changes only through `transition()` ([docs/domain/booking.md](docs/domain/booking.md)).
- Testing differs by side: frontend follows features-first ([docs/frontend.md](docs/frontend.md)), backend writes tests with the code ([docs/backend.md](docs/backend.md)).

### When finishing

Give a short summary: what changed, anything left undone or uncertain, and any doc that should change because of the work.

## Changing docs and making decisions

- Any decision that affects more than one person goes through a merge request that changes the relevant doc **and** adds an entry to [docs/decisions.md](docs/decisions.md). A decision made in a meeting counts once that merge request is merged; whoever proposed it opens it the same day.
- Never delete a decision; mark it superseded and add the new one.
- Who approves doc changes:

| Docs | Approved by |
| --- | --- |
| `docs/frontend.md`, `web/apps/CLAUDE.md`, `web/packages/CLAUDE.md` | One frontend engineer |
| `docs/backend.md`, `core/CLAUDE.md` | One backend engineer |
| `docs/operations.md`, `infra/CLAUDE.md` | One engineer working on DevOps |
| `docs/analytics.md` | One frontend engineer; the lead too if a metric's definition changes |
| Shared docs: this file, `product`, `glossary`, `architecture`, `core-boundaries`, `domain/*`, `api` | The lead and one engineer from each affected role |
| `docs/decisions.md`, `docs/demo-plan.md` | The lead |

Role docs need no sign-off from the other role. If a change affects what the other role relies on (an endpoint, an event, a shared package's API), it belongs in a shared doc instead. `.gitlab/CODEOWNERS` maps these owners.

Not in these docs: personal plans, secrets, task tracking (use the issue tracker).

## Git workflow

- Short-lived branches into `master`, the default branch; `master` is always deployable and protected (no direct pushes).
- One feature or fix per merge request; the pipeline must pass before merging.
- Changes to `core/`, `web/packages/` and `contracts/` are also reviewed by the lead, within one working day. Other changes are reviewed by the other engineer in the same role.
- Commit messages follow Conventional Commits: `feat(booking): add check-in action`, `fix(member): show denial reason`. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`.

### Definition of done

- [ ] Does what the task and the docs say, verified by a developer.
- [ ] Contract, generated client and backend agree (pipeline green).
- [ ] Loading, empty and error states handled (frontend).
- [ ] Tracking events added and listed in [docs/analytics.md](docs/analytics.md) (frontend).
- [ ] Storybook stories added or updated for new or changed components, once confirmed (frontend, [docs/frontend.md](docs/frontend.md)).
- [ ] Tests written per the frontend or backend guide, and passing.
- [ ] No product-specific code.
- [ ] Docs updated if anything they describe changed.
