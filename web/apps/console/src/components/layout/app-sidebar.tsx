import {
	Sidebar,
	SidebarContent,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	SidebarRail,
} from '@booking-core/ui';
import { Link, useLocation } from '@tanstack/react-router';
import { NAV_ITEMS } from './nav-items';

/** Console's collapsible icon sidebar, driven by `NAV_ITEMS`. */
export function AppSidebar() {
	const location = useLocation();

	return (
		<Sidebar className='bg-sidebar text-sidebar-foreground' collapsible='icon'>
			<SidebarHeader className='h-16 justify-center px-2'>
				<span className='text-sidebar-foreground truncate px-1.5 text-sm font-semibold tracking-wide'>
					Booking Core · Console
				</span>
			</SidebarHeader>

			<SidebarContent className='p-3'>
				<SidebarMenu>
					{NAV_ITEMS.map((item) => {
						const ItemIcon = item.icon;
						const isActive = location.pathname === item.to;

						return (
							<SidebarMenuItem key={item.to}>
								<SidebarMenuButton
									className='h-12 rounded-md text-sm'
									isActive={isActive}
									render={
										<Link className='flex items-center justify-start gap-3 px-3' to={item.to}>
											<ItemIcon className='size-4' />
											<span>{item.label}</span>
										</Link>
									}
									tooltip={item.label}
								/>
							</SidebarMenuItem>
						);
					})}
				</SidebarMenu>
			</SidebarContent>

			<SidebarRail />
		</Sidebar>
	);
}
