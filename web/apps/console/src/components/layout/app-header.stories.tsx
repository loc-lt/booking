import { SidebarProvider, ThemeSwitcher } from '@booking-core/ui';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { AppHeader, type AppHeaderProps } from './app-header';

const meta = {
	title: 'apps/console/AppHeader',
	component: AppHeader,
	tags: ['autodocs'],
	parameters: { layout: 'fullscreen' },
	args: {
		title: 'Resource types',
	},
} satisfies Meta<typeof AppHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

// `AppHeader` toggles the sidebar via `useSidebar()`, so every story needs a
// `SidebarProvider` above it.
function AppHeaderDemo(props: AppHeaderProps) {
	return (
		<SidebarProvider>
			<AppHeader {...props} />
		</SidebarProvider>
	);
}

export const Default: Story = {
	render: (args) => <AppHeaderDemo {...args} />,
};

export const WithSubtitle: Story = {
	args: { subtitle: 'What operators can configure per site' },
	render: (args) => <AppHeaderDemo {...args} />,
};

function WithThemeSwitcherDemo() {
	const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('light');

	return (
		<SidebarProvider>
			<AppHeader
				actions={<ThemeSwitcher onThemeChange={setTheme} theme={theme} />}
				title='Resource types'
			/>
		</SidebarProvider>
	);
}

export const WithActions: Story = {
	render: () => <WithThemeSwitcherDemo />,
};
