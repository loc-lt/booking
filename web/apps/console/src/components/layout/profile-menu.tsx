import {
	Avatar,
	AvatarFallback,
	AvatarImage,
	Button,
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
	Icon,
} from '@booking-core/ui';
import type { ReactNode } from 'react';

export interface ProfileMenuUser {
	name: string;
	avatarUrl?: string;
	/** Short text shown under the name, e.g. a role or email. */
	caption?: string;
}

export interface ProfileMenuItem {
	key: string;
	label: string;
	icon?: ReactNode;
	onSelect: () => void;
	variant?: 'default' | 'destructive';
}

export interface ProfileMenuProps {
	user: ProfileMenuUser;
	/** Extra items above the sign-out action, e.g. "View profile". */
	items?: ProfileMenuItem[];
	onSignOut?: () => void;
	signOutLabel?: string;
	isSigningOut?: boolean;
	menuLabel?: string;
}

function getInitials(name: string): string {
	return name
		.split(' ')
		.filter(Boolean)
		.slice(0, 2)
		.map((part) => part[0]?.toUpperCase())
		.join('');
}

/** Header avatar menu: identity, app-supplied `items`, and an optional sign-out action. No auth or role knowledge. */
export function ProfileMenu({
	user,
	items = [],
	onSignOut,
	signOutLabel = 'Sign out',
	isSigningOut = false,
	menuLabel = 'Open profile menu',
}: ProfileMenuProps) {
	return (
		<DropdownMenu>
			<DropdownMenuTrigger
				render={
					<Button
						aria-label={menuLabel}
						className='h-auto max-w-60 justify-start gap-2 p-2'
						type='button'
						variant='ghost'
					>
						<Avatar className='bg-accent size-8 rounded-full'>
							<AvatarImage alt={user.name} src={user.avatarUrl} />
							<AvatarFallback className='font-bold'>{getInitials(user.name)}</AvatarFallback>
						</Avatar>
					</Button>
				}
			/>
			<DropdownMenuContent align='end' className='min-w-48'>
				<DropdownMenuGroup>
					<DropdownMenuLabel className='p-0 font-normal'>
						<div className='flex flex-col items-center justify-center gap-2 p-2'>
							<Avatar className='bg-accent size-16 rounded-full'>
								<AvatarImage alt={user.name} src={user.avatarUrl} />
								<AvatarFallback className='text-2xl font-bold'>
									{getInitials(user.name)}
								</AvatarFallback>
							</Avatar>
							<div
								className='text-foreground truncate text-center text-base font-bold'
								title={user.name}
							>
								{user.name}
							</div>
							{user.caption ? (
								<div className='text-muted-foreground truncate text-center text-xs'>
									{user.caption}
								</div>
							) : null}
						</div>
					</DropdownMenuLabel>
				</DropdownMenuGroup>
				{items.length > 0 ? (
					<>
						<DropdownMenuSeparator />
						{items.map((item) => (
							<DropdownMenuItem key={item.key} onClick={item.onSelect} variant={item.variant}>
								{item.icon}
								{item.label}
							</DropdownMenuItem>
						))}
					</>
				) : null}
				{onSignOut ? (
					<>
						<DropdownMenuSeparator />
						<DropdownMenuItem disabled={isSigningOut} onClick={onSignOut} variant='destructive'>
							<Icon name='LogOut' />
							{signOutLabel}
						</DropdownMenuItem>
					</>
				) : null}
			</DropdownMenuContent>
		</DropdownMenu>
	);
}
