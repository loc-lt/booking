import { configureCoreClient } from '@booking-core/api-client';
import { CoreAppProvider } from '@booking-core/app-kit';
import { createRouter, RouterProvider } from '@tanstack/react-router';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { auth } from './auth';
import { routeTree } from './routeTree.gen';
import '@booking-core/ui/styles.css';

configureCoreClient({
	baseUrl: window.__CONFIG__.apiUrl,
	getToken: () => auth.getAccessToken(),
	getTenantId: () => auth.currentTenantId(),
});

const router = createRouter({ routeTree });

declare module '@tanstack/react-router' {
	interface Register {
		router: typeof router;
	}
}

// biome-ignore lint/style/noNonNullAssertion: index.html always provides #root
const root = document.getElementById('root')!;

createRoot(root).render(
	<StrictMode>
		<CoreAppProvider appName='member'>
			<RouterProvider router={router} />
		</CoreAppProvider>
	</StrictMode>,
);
