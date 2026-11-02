import { useTheme } from '@booking-core/app-kit';
import { ThemeSwitcher } from '@booking-core/ui';
import { createRootRoute, Outlet, useLocation } from '@tanstack/react-router';
import { AppHeader } from '@/components/layout/app-header';
import { AppShell } from '@/components/layout/app-shell';
import { AppSidebar } from '@/components/layout/app-sidebar';
import { NAV_ITEMS } from '@/components/layout/nav-items';

export const Route = createRootRoute({
	component: RootLayout,
});

function RootLayout() {
	const location = useLocation();
	const { setTheme, theme } = useTheme();
	const currentItem = NAV_ITEMS.find((item) => item.to === location.pathname);

	return (
		<AppShell
			header={
				<AppHeader
					actions={<ThemeSwitcher onThemeChange={setTheme} theme={theme} />}
					title={currentItem?.label ?? 'Booking Core · Console'}
				/>
			}
			sidebar={<AppSidebar />}
		>
			<Outlet />
		</AppShell>
	);
}
