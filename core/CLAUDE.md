# Core backend

@../docs/backend.md

The shared backend guide above gives the rules. The backend handbook in [docs/](docs/README.md)
says how this Django implementation follows them: [getting-started](docs/getting-started.md)
(run it, `.env`, tests), [structure](docs/structure.md) (every folder and file),
[request-lifecycle](docs/request-lifecycle.md), [data-and-tenancy](docs/data-and-tenancy.md),
[engines](docs/engines.md), [conventions](docs/conventions.md) (module template, how to add an
endpoint), [reading-guide](docs/reading-guide.md), [build-history](docs/build-history.md),
[build-walkthrough](docs/build-walkthrough.md) (folder by folder),
[open-decisions](docs/open-decisions.md), [api-table-map](docs/api-table-map.md).

Before changing code in `api/`: read `docs/conventions.md` and the row of `docs/engines.md`
for the engine you touch, then its test file. Run `python scripts/dev.py check` before opening
a merge request.
