# Decision log

Every decision that affects more than one person is recorded here, in the same merge request that changes the docs. Add new entries at the bottom with the next number (D-001, D-002, …). Never delete an entry: mark it "Superseded by D-0xx" and add the new one. Longer reasoning can go in `docs/decisions/D-0xx.md`.

| ID | Date | Decision | Why | Rejected |
| --- | --- | --- | --- | --- |
| D-001 | 2026-10-31 | One Storybook instance (`web/storybook`, `@storybook/react-vite`) scans `web/packages/*/src` and `web/apps/*/src` for `*.stories.tsx`, instead of a Storybook per package. `msw-storybook-addon` reuses the existing scenario handlers from `@booking-core/api-client` so component stories can exercise real mutations against the same mock data apps use. | Lets engineers preview and test a component in isolation, without wiring it into a page, while it's being changed. One instance avoids duplicating Storybook's config and dependencies across six workspace members; reusing the scenario handlers avoids a second, divergent mock layer. | A Storybook per package — rejected as unnecessary duplication for an internal, non-published monorepo. |
