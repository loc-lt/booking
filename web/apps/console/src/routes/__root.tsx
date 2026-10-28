import { createRootRoute, Link, Outlet } from '@tanstack/react-router';

export const Route = createRootRoute({
	component: RootLayout,
});

function RootLayout() {
	return (
		<div className='min-h-dvh'>
			<header className='flex items-center gap-4 border-b p-4'>
				<span className='font-semibold'>Booking Core · Console</span>
				<Link to='/resource-types' className='text-sm hover:underline'>
					Resource types
				</Link>
			</header>
			<Outlet />
		</div>
	);
}
