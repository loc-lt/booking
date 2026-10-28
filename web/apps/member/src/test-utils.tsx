import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type RenderResult, render } from '@testing-library/react';
import type { ReactElement } from 'react';

/** Renders a component wrapped in a fresh QueryClientProvider, for tests that use the api-client hooks. */
export function renderWithQueryClient(ui: ReactElement): RenderResult {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
	});
	return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}
