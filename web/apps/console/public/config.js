// Local dev default. In every other environment this file is written by
// infra/web/40-runtime-config.sh at container start; see docs/operations.md.
window.__CONFIG__ = {
	app: 'console',
	apiUrl: '',
	apiMode: 'mock',
	posthogKey: '',
	sentryDsn: '',
};
