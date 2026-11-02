import { SidebarInset, SidebarProvider } from '@booking-core/ui';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { Outlet } from '@tanstack/react-router';
import { AppSidebar } from './app-sidebar';
import { StorybookRouterProvider } from './storybook-router';

const meta = {
	title: 'apps/console/AppSidebar',
	component: AppSidebar,
	tags: ['autodocs'],
	parameters: { layout: 'fullscreen' },
} satisfies Meta<typeof AppSidebar>;

export default meta;
type Story = StoryObj<typeof meta>;

function Shell() {
	return (
		<SidebarProvider>
			<AppSidebar />
			<SidebarInset>
				<Outlet />
			</SidebarInset>
		</SidebarProvider>
	);
}

export const ResourceTypesActive: Story = {
	render: () => <StorybookRouterProvider initialPath='/resource-types' shell={Shell} />,
};

export const ApprovalsActive: Story = {
	render: () => <StorybookRouterProvider initialPath='/approvals' shell={Shell} />,
};
