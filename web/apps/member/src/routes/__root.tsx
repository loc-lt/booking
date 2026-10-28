import { createRootRoute, Outlet } from '@tanstack/react-router';

export const Route = createRootRoute({
	component: RootLayout,
});

function RootLayout() {
	return (
		<div className='min-h-dvh'>
			<header className='border-b p-4'>
				<span className='font-semibold'>Booking Core · Member</span>
			</header>
			<Outlet />
		</div>
	);
}
