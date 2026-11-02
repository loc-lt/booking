import type { Meta, StoryObj } from '@storybook/react-vite';
import { LayoutDashboard, ListChecks, Settings } from 'lucide-react';
import {
	Sidebar,
	SidebarContent,
	SidebarFooter,
	SidebarHeader,
	SidebarInset,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	SidebarProvider,
	SidebarRail,
	SidebarTrigger,
} from './sidebar';

const ITEMS = [
	{ key: 'overview', label: 'Overview', icon: LayoutDashboard, isActive: true },
	{ key: 'tasks', label: 'Tasks', icon: ListChecks, isActive: false },
	{ key: 'settings', label: 'Settings', icon: Settings, isActive: false },
];

const meta = {
	title: 'ui/Sidebar',
	component: Sidebar,
	tags: ['autodocs'],
	parameters: { layout: 'fullscreen' },
} satisfies Meta<typeof Sidebar>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * The raw primitives this component library exposes. `@booking-core/ui`
 * doesn't ship an app-shell composition on top of these — each app composes
 * its own (see `apps/console/src/components/layout/AppSidebar`), since the
 * nav items, links and active-route state are app-specific.
 */
export const Default: Story = {
	render: () => (
		<SidebarProvider>
			<Sidebar collapsible='icon'>
				<SidebarHeader className='h-16 justify-center px-2'>
					<span className='truncate px-1.5 text-sm font-semibold'>Example App</span>
				</SidebarHeader>
				<SidebarContent className='p-3'>
					<SidebarMenu>
						{ITEMS.map((item) => {
							const ItemIcon = item.icon;

							return (
								<SidebarMenuItem key={item.key}>
									<SidebarMenuButton
										className='h-12 rounded-md text-sm'
										isActive={item.isActive}
										tooltip={item.label}
									>
										<ItemIcon className='size-4' />
										<span>{item.label}</span>
									</SidebarMenuButton>
								</SidebarMenuItem>
							);
						})}
					</SidebarMenu>
				</SidebarContent>
				<SidebarFooter className='px-3 py-2'>
					<div className='text-sidebar-foreground/60 text-center text-xs'>v0.0.0</div>
				</SidebarFooter>
				<SidebarRail />
			</Sidebar>
			<SidebarInset>
				<div className='border-border flex h-16 items-center gap-3 border-b px-4'>
					<SidebarTrigger />
					<span className='font-semibold'>Overview</span>
				</div>
				<div className='p-6'>
					<p className='text-muted-foreground text-sm'>
						Content area — resize or use the trigger to collapse the sidebar.
					</p>
				</div>
			</SidebarInset>
		</SidebarProvider>
	),
};

export const Collapsed: Story = {
	render: () => (
		<SidebarProvider defaultOpen={false}>
			<Sidebar collapsible='icon'>
				<SidebarHeader className='h-16 justify-center px-2'>
					<span className='truncate px-1.5 text-sm font-semibold'>Example App</span>
				</SidebarHeader>
				<SidebarContent className='p-3'>
					<SidebarMenu>
						{ITEMS.map((item) => {
							const ItemIcon = item.icon;

							return (
								<SidebarMenuItem key={item.key}>
									<SidebarMenuButton
										className='h-12 rounded-md text-sm'
										isActive={item.isActive}
										tooltip={item.label}
									>
										<ItemIcon className='size-4' />
										<span>{item.label}</span>
									</SidebarMenuButton>
								</SidebarMenuItem>
							);
						})}
					</SidebarMenu>
				</SidebarContent>
				<SidebarRail />
			</Sidebar>
			<SidebarInset>
				<div className='border-border flex h-16 items-center gap-3 border-b px-4'>
					<SidebarTrigger />
					<span className='font-semibold'>Overview</span>
				</div>
			</SidebarInset>
		</SidebarProvider>
	),
};
