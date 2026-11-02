import { cn } from 'cn';
import type { ReactNode } from 'react';

export interface PageContainerProps {
	children: ReactNode;
	className?: string;
}

/** Standard content wrapper for a page rendered inside `AppShell`. */
export function PageContainer({ children, className }: PageContainerProps) {
	return (
		<main className={cn('bg-background min-h-[calc(100svh-4rem)] min-w-0 p-3', className)}>
			{children}
		</main>
	);
}
