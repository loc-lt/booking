import { cn } from 'cn';
import { icons, Loader } from 'lucide-react';
import type { CSSProperties } from 'react';

type Props = {
	className?: string;
	style?: CSSProperties;
	isLoading?: boolean;
	name: keyof typeof icons;
	onClick?: () => void;
};

/** Renders a lucide icon by name, swapping in a spinner while `isLoading`. */
export function Icon({ className, style, isLoading, name, onClick }: Props) {
	const Component = isLoading ? Loader : icons[name];

	return (
		<Component
			aria-hidden='true'
			className={cn('size-4 shrink-0', isLoading && 'animate-spin', className)}
			onClick={onClick}
			style={style}
		/>
	);
}
