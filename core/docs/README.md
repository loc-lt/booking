# Backend handbook

Documentation for the people and agents who work in `core/api/`: the Django implementation of
`contracts/openapi.yaml`, its worker, its tests and its tooling. Everything here is specific to
the backend. The product, the domain and the API contract are described once, for both
frontend and backend, in the shared docs under [`../../docs/`](../../docs/); this handbook links
to them instead of copying them, because the root `CLAUDE.md` makes those files the single
source of truth and a copy would drift.

## Read in this order

| # | Document | Answers | Time |
| --- | --- | --- | --- |
| 1 | [getting-started.md](getting-started.md) | How do I run it, sign in, run the tests, and where is the configuration? | 10 min |
| 2 | [structure.md](structure.md) | What is each folder and file for, and why is it named that way? | 20 min |
| 3 | [request-lifecycle.md](request-lifecycle.md) | What happens to one HTTP request, from Caddy to the database and back; what the worker does | 15 min |
| 4 | [data-and-tenancy.md](data-and-tenancy.md) | The 28 tables, who owns them, row-level security, composite foreign keys, migrations | 15 min |
| 5 | [engines.md](engines.md) | The thirteen guarantees the core gives and the file and test that prove each | 15 min |
| 6 | [conventions.md](conventions.md) | The module template, how to add an endpoint, errors, serializers, tests, lint | 15 min |
| 7 | [reading-guide.md](reading-guide.md) | A senior engineer's path through the code, first file to last, with the question each stop answers | 2 h with the code open |
| 8 | [build-history.md](build-history.md) | How the backend was built from an empty folder: order, reasons, what changed from the plan (the short version) | 20 min |
| 9 | [build-walkthrough.md](build-walkthrough.md) | The same story folder by folder: why each folder and file was created at that point, why it has its name, what each file does | 45 min |
| 10 | [open-decisions.md](open-decisions.md) | Choices the code makes that the shared docs do not yet record, and who must approve them | 10 min |
| 11 | [api-table-map.md](api-table-map.md) | For each of the 69 operations, the tables it reads and writes, measured by running the scenario | Reference |

An agent that has to change the backend should read 1, 2, 3 and 6 before touching code, and
the relevant row of 5 for the engine it changes.

## Shared docs this handbook depends on

Read these from the shared folder; they are owned by the lead and both roles.

| Shared doc | Read it when | What the backend takes from it |
| --- | --- | --- |
| [`docs/backend.md`](../../docs/backend.md) | Always, first | The rules every backend change follows: one service call per route, one transaction, `transition()` only, tests with the code. Owned by the backend engineers. **Its "Structure", "Libraries" and table list still describe the Flask plan; decision D-002 updates them** ([open-decisions.md](open-decisions.md)). |
| [`docs/api.md`](../../docs/api.md) | Any endpoint | Naming, pagination, headers, the error codes, the contract workflow |
| [`docs/domain/booking.md`](../../docs/domain/booking.md) | Booking features | The seven pipeline steps, the nine statuses, the allowed moves, payment as a policy |
| [`docs/domain/rules.md`](../../docs/domain/rules.md) | Rules | Scope, stage, condition, effect, priority; evaluation order; the trace |
| [`docs/domain/configuration.md`](../../docs/domain/configuration.md) | Settings, custom fields | Versioned config, field scopes and types, type changes as migrations |
| [`docs/domain/events.md`](../../docs/domain/events.md) | Anything that reacts to a change | The outbox, what an event carries, the catalogue |
| [`docs/core-boundaries.md`](../../docs/core-boundaries.md) | Every change | No product or customer logic in the core; the three-customer rule |
| [`docs/architecture.md`](../../docs/architecture.md) | Once | Module list, repo layout, how products use the core |
| [`docs/operations.md`](../../docs/operations.md) | Docker, CI, deploy | Environments, images, pipeline, secrets |
| [`docs/decisions.md`](../../docs/decisions.md) | Before changing a convention | The decision log (D-001 … ) |
| [`docs/examples/`](../../docs/examples/) | When a doc points there | Example payloads, the SQL of tenant isolation and the no-double-booking constraint |

## Other places that describe this code

- [`../api/README.md`](../api/README.md): the short entry page of the package (run, layout, dependencies: `pyproject.toml` + `uv.lock`).
- `http://localhost:8000/api/docs` when the stack runs: Swagger UI for every endpoint, ReDoc, the contract, and every markdown file of this repository rendered in the browser.
- The team's notes folder next to this repository (`../../../docs/`, Vietnamese): the API test scenario (`KICH_BAN_TEST_API.md`), the flow diagram (`SO_DO_LUONG_API.html`), the database design (`database/`), and the Postman collection that proves the API (`postman/`). [api-table-map.md](api-table-map.md) is generated from that scenario.

## Keeping this handbook true

- A merge request that changes a folder, a file's role, an engine or a convention updates the matching document here. Reviewers check it like code.
- `api-table-map.md` is generated: run `python docs/postman/trace/trace_run.py` then `python docs/postman/flows_build.py` from the notes folder after changing the scenario.
- These documents are owned by the backend engineers (same as `docs/backend.md` in the root `CLAUDE.md`). Anything that changes what the frontend relies on (an endpoint, an event, an error code) belongs in a shared doc and in the contract, not here.
