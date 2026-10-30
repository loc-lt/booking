import { QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode, useEffect, useState } from 'react';
import { getRuntimeConfig } from './config';
import { ErrorBoundary } from './ErrorBoundary';
import { startMocking } from './mocking';
import { createQueryClient } from './queryClient';
import { initTracking } from './tracking';

export interface CoreAppProviderProps {
	/** Tags tracking and error reports, e.g. "console" or "member". */
	appName: string;
	children: ReactNode;
}

/**
 * Wraps a reference app's router: creates the query client, starts the mock
 * API when `apiMode` is "mock", starts PostHog/Sentry, and renders a
 * top-level error boundary. Call `configureCoreClient` before rendering
 * this. See docs/frontend.md and docs/analytics.md.
 */
export function CoreAppProvider({ appName, children }: CoreAppProviderProps) {
	const [queryClient] = useState(createQueryClient);
	const [ready, setReady] = useState(() => getRuntimeConfig().apiMode !== 'mock');

	useEffect(() => {
		initTracking(appName);
	}, [appName]);

	useEffect(() => {
		if (getRuntimeConfig().apiMode === 'mock') {
			startMocking().then(() => setReady(true));
		}
	}, []);

	if (!ready) {
		return null;
	}

	return (
		<ErrorBoundary>
			<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
		</ErrorBoundary>
	);
}
