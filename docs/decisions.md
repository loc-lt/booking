# Decision log

Every decision that affects more than one person is recorded here, in the same merge request that changes the docs. Add new entries at the bottom with the next number (D-001, D-002, …). Never delete an entry: mark it "Superseded by D-0xx" and add the new one. Longer reasoning can go in `docs/decisions/D-0xx.md`.

| ID | Date | Decision | Why | Rejected |
| --- | --- | --- | --- | --- |
| D-001 | 2026-11-02 | Frontend source files (components, hooks, utils) use kebab-case filenames, e.g. `booking-card.tsx`, `use-booking-calendar-data.ts`. | The `ui` package's shadcn-added and hand-built components were already kebab-case; every other package and both apps' features were PascalCase/camelCase, so the two styles sat side by side in the same tree. | Keeping PascalCase for components and camelCase for hooks/utils (the pre-existing majority) — rejected because it kept `web/packages/ui` as a permanent exception rather than resolving it. |
