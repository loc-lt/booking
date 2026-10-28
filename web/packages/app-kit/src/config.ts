export interface RuntimeConfig {
	app: string;
	apiUrl: string;
	apiMode: 'mock' | 'real';
	posthogKey: string;
	sentryDsn: string;
}

declare global {
	interface Window {
		__CONFIG__: RuntimeConfig;
	}
}

/** Reads the environment values written into `config.js`. See docs/operations.md. */
export function getRuntimeConfig(): RuntimeConfig {
	return window.__CONFIG__;
}
