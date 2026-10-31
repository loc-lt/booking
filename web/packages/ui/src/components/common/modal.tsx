import type { ReactElement, ReactNode } from 'react';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from '../ui/dialog';

type Props = {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	title?: ReactNode;
	description?: ReactNode;
	trigger?: ReactElement;
	children: ReactNode;
};

export function Modal({ open, onOpenChange, title, description, trigger, children }: Props) {
	return (
		<Dialog onOpenChange={onOpenChange} open={open}>
			{trigger && <DialogTrigger render={trigger} />}
			<DialogContent>
				{(title || description) && (
					<DialogHeader>
						{title && <DialogTitle className='text-2xl font-bold'>{title}</DialogTitle>}
						{description && <DialogDescription>{description}</DialogDescription>}
					</DialogHeader>
				)}
				{children}
			</DialogContent>
		</Dialog>
	);
}
