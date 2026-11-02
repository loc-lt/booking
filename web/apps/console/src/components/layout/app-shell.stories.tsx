import { ThemeSwitcher } from '@booking-core/ui';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { Outlet, useLocation } from '@tanstack/react-router';
import { useState } from 'react';
import { AppHeader } from './app-header';
import { AppShell } from './app-shell';
import { AppSidebar } from './app-sidebar';
import { NAV_ITEMS } from './nav-items';
import { StorybookRouterProvider } from './storybook-router';

const meta = {
	title: 'apps/console/AppShell',
	component: AppShell,
	tags: ['autodocs'],
	parameters: { layout: 'fullscreen' },
	// Every story below supplies its own `render`, which composes the real
	// sidebar/header/content itself — these placeholders only satisfy
	// `AppShell`'s required props so `StoryObj` doesn't demand real ones too.
	args: { sidebar: null, header: null, children: null },
} satisfies Meta<typeof AppShell>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Mirrors `routes/__root.tsx` — the console app's actual root layout. */
function RootLayout() {
	const location = useLocation();
	const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('light');
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

/** Click a sidebar item or the theme switcher — both work against a real (in-memory) router and state. */
export const Default: Story = {
	render: () => <StorybookRouterProvider shell={RootLayout} />,
};

export const Approvals: Story = {
	render: () => <StorybookRouterProvider initialPath='/approvals' shell={RootLayout} />,
};
