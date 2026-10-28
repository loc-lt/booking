import { handlers } from '@booking-core/api-client';

let worker: Promise<void> | null = null;

/**
 * Starts the MSW browser worker with the shared mock handlers. Safe to call
 * more than once; the worker only starts once per page load.
 */
export function startMocking(): Promise<void> {
	if (!worker) {
		worker = import('msw/browser').then(async ({ setupWorker }) => {
			await setupWorker(...handlers).start({ onUnhandledRequest: 'bypass' });
		});
	}
	return worker;
}
