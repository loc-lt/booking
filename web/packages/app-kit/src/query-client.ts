import { QueryClient } from '@tanstack/react-query';
import { getRuntimeConfig } from './config';

/** Used when `window.__CONFIG__.staleTimeMinutes` isn't set. */
export const DEFAULT_STALE_TIME_MINUTES = 5;

export function createQueryClient(): QueryClient {
	const staleTimeMinutes = getRuntimeConfig().staleTimeMinutes ?? DEFAULT_STALE_TIME_MINUTES;

	return new QueryClient({
		defaultOptions: {
			queries: {
				refetchOnWindowFocus: false,
				retry: false,
				staleTime: staleTimeMinutes * 60_000,
			},
		},
	});
}
