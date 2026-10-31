// Local dev default. In every other environment this file is written by
// infra/web/40-runtime-config.sh at container start; see docs/operations.md.
//
// Points at the shared mock server (web/mock-server) so this app and member
// see the same data — a resource type created here shows up in member, a
// booking made in member shows up in this app's approvals/bookings. Run it
// with `pnpm --filter mock-server dev`. For solo work with no other process
// to run, switch back to `apiMode: 'mock'` (each tab gets its own throwaway
// data instead). See docs/frontend.md's "Mocks" section.
window.__CONFIG__ = {
	app: 'console',
	apiUrl: 'http://localhost:4000',
	apiMode: 'real',
	posthogKey: 'phc_xj9MDfLy5MmommnT7JUcvNqb2SmPbdJQsgnJgeWxPnEt',
	sentryDsn:
		'https://226fb830f1727fd1efb6b21d40bfe79f@o4512342763307008.ingest.us.sentry.io/4512343280254976',
	// Minutes a query stays fresh before TanStack Query refetches it. See
	// app-kit's queryClient.ts — refetchOnWindowFocus and retry are off, so
	// after this window a screen only gets fresher data on remount or an
	// explicit invalidateQueries() call, not automatically.
	staleTimeMinutes: 5,
};
