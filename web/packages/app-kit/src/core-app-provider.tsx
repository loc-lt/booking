import { TooltipProvider } from '@booking-core/ui';
import { QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode, useEffect, useState } from 'react';
import { getRuntimeConfig } from './config';
import { ErrorBoundary } from './error-boundary';
import { startMocking } from './mocking';
import { createQueryClient } from './query-client';
import { type Theme, ThemeProvider } from './theme-provider';
import { initTracking } from './tracking';

export interface CoreAppProviderProps {
	/** Tags tracking and error reports, e.g. "console" or "member". */
	appName: string;
	children: ReactNode;
	/** Passed through to `ThemeProvider`. Defaults to `"system"`. */
	defaultTheme?: Theme;
	/** Passed through to `ThemeProvider` as `storageKey`. */
	themeStorageKey?: string;
}

/**
 * Wraps a reference app's router: creates the query client, starts the mock
 * API when `apiMode` is "mock", starts PostHog/Sentry, renders a top-level
 * error boundary, and shares one `ThemeProvider` and `TooltipProvider` so
 * every app gets light/dark theming and consistent `IconButton` hover delay
 * for free. Call `configureCoreClient` before rendering this. See
 * docs/frontend.md and docs/analytics.md.
 */
export function CoreAppProvider({
	appName,
	children,
	defaultTheme,
	themeStorageKey,
}: CoreAppProviderProps) {
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
			<QueryClientProvider client={queryClient}>
				<ThemeProvider defaultTheme={defaultTheme} storageKey={themeStorageKey}>
					<TooltipProvider>{children}</TooltipProvider>
				</ThemeProvider>
			</QueryClientProvider>
		</ErrorBoundary>
	);
}
