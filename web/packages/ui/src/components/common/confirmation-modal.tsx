import { useHotkey } from '@tanstack/react-hotkeys';
import type { icons } from 'lucide-react';
import { type ReactNode, useRef } from 'react';
import { Button } from '../ui/button';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from '../ui/dialog';
import { Icon } from './icon';

type Props = {
	cancelLabel: string;
	children?: ReactNode;
	confirmLabel: string;
	/** Disables just the confirm button (e.g. a required field in `children` isn't filled in yet) without the loading semantics of `isConfirming`. */
	confirmDisabled?: boolean;
	dangerous?: boolean;
	description?: ReactNode;
	/** Confirm-button icon. Defaults to `Trash` when `dangerous`, `Check` otherwise. */
	icon?: keyof typeof icons;
	isConfirming?: boolean;
	open: boolean;
	title: ReactNode;
	onConfirm: () => void;
	onOpenChange: (open: boolean) => void;
};

export function ConfirmationModal({
	cancelLabel,
	children,
	confirmLabel,
	confirmDisabled = false,
	dangerous = false,
	description,
	icon,
	isConfirming,
	open,
	title,
	onConfirm,
	onOpenChange,
}: Props) {
	useHotkey(
		'Escape',
		() => {
			if (open && !isConfirming) {
				onOpenChange(false);
			}
		},
		{
			conflictBehavior: 'allow',
			preventDefault: true,
			requireReset: true,
		},
	);

	const cancelButtonRef = useRef<HTMLButtonElement>(null);
	const confirmButtonRef = useRef<HTMLButtonElement>(null);

	const cancelButton = (
		<Button
			disabled={isConfirming}
			onClick={() => onOpenChange(false)}
			ref={cancelButtonRef}
			type='button'
			variant='outline'
		>
			{cancelLabel}
		</Button>
	);

	const confirmButton = (
		<Button
			disabled={isConfirming || confirmDisabled}
			onClick={onConfirm}
			ref={confirmButtonRef}
			type='button'
			variant={dangerous ? 'destructive' : 'default'}
		>
			<Icon isLoading={isConfirming} name={icon ?? (dangerous ? 'Trash' : 'Check')} />
			{confirmLabel}
		</Button>
	);

	return (
		<Dialog onOpenChange={onOpenChange} open={open}>
			<DialogContent
				// Base UI's default initial-focus behavior would otherwise focus the
				// first tabbable element in DOM order — which, in `dangerous` mode,
				// is the confirm button (see the reordered footer below), not
				// whichever button should actually receive focus.
				initialFocus={() => (dangerous ? cancelButtonRef : confirmButtonRef).current}
			>
				<DialogHeader>
					<DialogTitle>{title}</DialogTitle>
					{description ? <DialogDescription>{description}</DialogDescription> : null}
				</DialogHeader>

				{children}

				<DialogFooter>
					{dangerous ? (
						<>
							{confirmButton}
							{cancelButton}
						</>
					) : (
						<>
							{cancelButton}
							{confirmButton}
						</>
					)}
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
