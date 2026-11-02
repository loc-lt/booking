export interface LoadingProps {
	label?: string;
}

function Spinner({ label = 'Loading…' }: LoadingProps) {
	return (
		<div className='text-muted-foreground flex items-center gap-3 text-sm'>
			<div className='border-border border-t-primary size-4 animate-spin rounded-full border-2' />
			<span>{label}</span>
		</div>
	);
}

/** Full-screen loading state, for routes with no layout shell mounted above them yet. See `PageLoading` for the compact variant. */
export function AppLoading({ label }: LoadingProps) {
	return (
		<div className='grid min-h-svh place-items-center p-6'>
			<Spinner label={label} />
		</div>
	);
}

/** Compact loading state for content rendered inside an already-mounted `AppShell`. See `AppLoading` for the full-screen variant. */
export function PageLoading({ label }: LoadingProps) {
	return (
		<div className='flex min-h-64 items-center justify-center p-6'>
			<Spinner label={label} />
		</div>
	);
}
