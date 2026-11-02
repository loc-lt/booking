import {
	createMemoryHistory,
	createRootRoute,
	createRoute,
	createRouter,
	RouterProvider,
} from '@tanstack/react-router';
import type { ReactNode } from 'react';
import { NAV_ITEMS } from './nav-items';

/**
 * A router whose root route renders `shell` (typically `AppSidebar`/
 * `AppHeader` composed around an `Outlet`), with one child route per
 * `NAV_ITEMS` entry rendering a placeholder page. For stories that exercise
 * real navigation — these components use TanStack Router's typed `Link`
 * directly rather than a generic `href` slot, so they need an actual router
 * context to render in Storybook.
 */
export function StorybookRouterProvider({
	initialPath = '/resource-types',
	shell,
}: {
	initialPath?: string;
	shell: () => ReactNode;
}) {
	const rootRoute = createRootRoute({ component: shell });
	const routes = NAV_ITEMS.map((item) =>
		createRoute({
			getParentRoute: () => rootRoute,
			path: item.to,
			component: () => (
				<div className='p-6'>
					<p className='text-muted-foreground text-sm'>"{item.label}" page content goes here.</p>
				</div>
			),
		}),
	);

	const router = createRouter({
		routeTree: rootRoute.addChildren(routes),
		history: createMemoryHistory({ initialEntries: [initialPath] }),
	});

	return <RouterProvider router={router} />;
}
