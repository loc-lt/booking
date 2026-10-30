export interface RuntimeConfig {
	app: string;
	apiUrl: string;
	apiMode: 'mock' | 'real';
	posthogKey: string;
	sentryDsn: string;
	/** How long a query stays fresh before TanStack Query refetches it. Falls back to DEFAULT_STALE_TIME_MINUTES (queryClient.ts) when unset. */
	staleTimeMinutes?: number;
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
