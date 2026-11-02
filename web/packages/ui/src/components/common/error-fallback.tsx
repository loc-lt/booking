import { cn } from 'cn';
import { Button } from '../ui/button';
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/card';
import { Icon } from './icon';

export interface ErrorFallbackProps {
	error: unknown;
	onRetry: () => void;
	/**
	 * `'inline'` fits within an already-mounted layout's content area instead
	 * of centering in the full viewport. Defaults to `'full'`.
	 */
	variant?: 'full' | 'inline';
	title?: string;
	retryLabel?: string;
}

function getErrorMessage(error: unknown): string {
	if (error instanceof Error && error.message) {
		return error.message;
	}

	if (typeof error === 'string' && error) {
		return error;
	}

	return 'An unexpected error occurred.';
}

/** Generic error card for a render-error boundary or a router's error component. */
export function ErrorFallback({
	error,
	onRetry,
	variant = 'full',
	title = 'Something went wrong',
	retryLabel = 'Try again',
}: ErrorFallbackProps) {
	return (
		<div className={cn('grid place-items-center p-6', variant === 'full' && 'min-h-svh')}>
			<Card className='w-full max-w-sm text-center'>
				<CardHeader>
					<Icon className='text-destructive mx-auto block size-8' name='TriangleAlert' />
					<CardTitle>{title}</CardTitle>
					<CardDescription>{getErrorMessage(error)}</CardDescription>
				</CardHeader>
				<CardFooter className='justify-center'>
					<Button onClick={onRetry}>{retryLabel}</Button>
				</CardFooter>
			</Card>
		</div>
	);
}
