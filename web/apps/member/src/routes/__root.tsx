import { createRootRoute, Link, Outlet } from '@tanstack/react-router';

export const Route = createRootRoute({
	component: RootLayout,
});

function RootLayout() {
	return (
		<div className='min-h-dvh'>
			<header className='flex items-center gap-4 border-b p-4'>
				<span className='font-semibold'>Booking Core · Member</span>
				<nav className='flex gap-3 text-sm'>
					<Link to='/' activeProps={{ className: 'font-medium' }}>
						Search
					</Link>
					<Link to='/bookings' activeProps={{ className: 'font-medium' }}>
						My bookings
					</Link>
				</nav>
			</header>
			<Outlet />
		</div>
	);
}
