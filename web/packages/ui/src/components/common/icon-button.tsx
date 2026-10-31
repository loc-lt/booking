import type { ComponentProps } from 'react';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { Icon } from './icon';

type Props = Omit<ComponentProps<typeof Button>, 'aria-label' | 'children'> & {
	icon: ComponentProps<typeof Icon>['name'];
	iconClassName?: string;
	label: string;
};

/**
 * An icon-only `Button` with its accessible name shown as a tooltip.
 * `CoreAppProvider` (`@booking-core/app-kit`) already wraps the app in one
 * shared `TooltipProvider`, so the hover delay feels consistent between
 * adjacent buttons without each `IconButton` needing its own.
 */
export function IconButton({ icon, iconClassName, label, ...props }: Props) {
	return (
		<Tooltip>
			<TooltipTrigger
				render={
					<Button aria-label={label} size='icon' type='button' {...props}>
						<Icon className={iconClassName} name={icon} />
					</Button>
				}
			/>
			<TooltipContent>{label}</TooltipContent>
		</Tooltip>
	);
}
