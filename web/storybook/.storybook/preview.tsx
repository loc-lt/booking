import '@booking-core/ui/styles.css';

import { handlers, resetBookingsScenario, resetResourceTypesScenario } from '@booking-core/api-client';
import { TooltipProvider } from '@booking-core/ui';
import type { Preview } from '@storybook/react-vite';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setupWorker } from 'msw/browser';
import { mswLoader } from 'msw-storybook-addon/csf3';
import { useState } from 'react';

const preview: Preview = {
	parameters: {
		layout: 'centered',
	},
	loaders: [
		mswLoader(async () => {
			const worker = setupWorker(...handlers);
			await worker.start({ onUnhandledRequest: 'bypass' });
			return worker;
		}),
	],
	// Scenario state (e.g. a booking approved by one story) otherwise leaks
	// into the next story, since the MSW worker and its in-memory data stay
	// alive across story switches within one Storybook session.
	beforeEach: () => {
		resetResourceTypesScenario();
		resetBookingsScenario();
	},
	decorators: [
		(Story) => {
			const [queryClient] = useState(
				() => new QueryClient({ defaultOptions: { queries: { retry: false } } }),
			);

			return (
				<QueryClientProvider client={queryClient}>
					<TooltipProvider>
						<Story />
					</TooltipProvider>
				</QueryClientProvider>
			);
		},
	],
};

export default preview;
