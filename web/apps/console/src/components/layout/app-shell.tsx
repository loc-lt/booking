import { PageContainer, SidebarInset, SidebarProvider } from '@booking-core/ui';
import type { ReactNode } from 'react';

export interface AppShellProps {
	/** Typically an `AppSidebar`. */
	sidebar: ReactNode;
	/** Typically an `AppHeader`. */
	header: ReactNode;
	children: ReactNode;
	/** Applied to the `PageContainer` wrapping `children`. */
	contentClassName?: string;
}

/** Console's collapsible-sidebar shell. */
export function AppShell({ sidebar, header, children, contentClassName }: AppShellProps) {
	return (
		<SidebarProvider>
			{sidebar}
			<SidebarInset>
				{header}
				<PageContainer className={contentClassName}>{children}</PageContainer>
			</SidebarInset>
		</SidebarProvider>
	);
}
