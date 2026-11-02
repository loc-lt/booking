import { Button, Icon, useSidebar } from '@booking-core/ui';
import type { ReactNode } from 'react';

export interface AppHeaderProps {
	title: string;
	subtitle?: string;
	/** Right-aligned extras before `menu`, e.g. a `ThemeSwitcher` or a notification bell. */
	actions?: ReactNode;
	/** Rendered at the far right, typically a `ProfileMenu`. */
	menu?: ReactNode;
	toggleSidebarLabel?: string;
}

/** Sticky top bar: sidebar toggle, page title, and app-supplied `actions`/`menu` slots. */
export function AppHeader({
	title,
	subtitle,
	actions,
	menu,
	toggleSidebarLabel = 'Toggle sidebar',
}: AppHeaderProps) {
	const { toggleSidebar } = useSidebar();

	return (
		<div className='border-border bg-card/95 supports-backdrop-filter:bg-card/80 sticky top-0 z-30 flex h-16 items-center justify-between border-b px-4 shadow-sm backdrop-blur'>
			<div className='flex min-w-0 items-center gap-x-4'>
				<Button
					aria-label={toggleSidebarLabel}
					onClick={toggleSidebar}
					size='icon-lg'
					variant='ghost'
				>
					<Icon name='Menu' />
				</Button>

				<div className='min-w-0'>
					<h1 className='truncate text-lg leading-tight font-semibold'>{title}</h1>
					{subtitle ? <p className='text-muted-foreground truncate text-xs'>{subtitle}</p> : null}
				</div>
			</div>

			<div className='flex items-center gap-x-2'>
				{actions}
				{menu}
			</div>
		</div>
	);
}
