import { cn } from 'cn';
import type { ReactNode } from 'react';
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/card';
import { Icon } from './icon';

export interface NotFoundProps {
	/**
	 * `'inline'` fits within an already-mounted layout's content area instead
	 * of centering in the full viewport. Defaults to `'full'`.
	 */
	variant?: 'full' | 'inline';
	title?: string;
	description?: string;
	/** Typically a link back to a safe route, e.g. a router `Link` wrapped in `Button`. */
	action?: ReactNode;
}

/** Generic 404 card. Pair with your router's own `notFoundComponent`/`defaultNotFoundComponent`. */
export function NotFound({
	variant = 'full',
	title = 'Page not found',
	description = "The page you're looking for doesn't exist or has moved.",
	action,
}: NotFoundProps) {
	return (
		<div className={cn('grid place-items-center p-6', variant === 'full' && 'min-h-svh')}>
			<Card className='w-full max-w-sm text-center'>
				<CardHeader>
					<Icon className='text-muted-foreground mx-auto block size-8' name='SearchX' />
					<CardTitle>{title}</CardTitle>
					<CardDescription>{description}</CardDescription>
				</CardHeader>
				{action ? <CardFooter className='justify-center'>{action}</CardFooter> : null}
			</Card>
		</div>
	);
}
