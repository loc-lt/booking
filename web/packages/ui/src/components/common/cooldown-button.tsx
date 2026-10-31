import type { ComponentProps, ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { Button } from '../ui/button';

type Props = ComponentProps<typeof Button> & {
	/** Seconds the button stays disabled after a click. */
	cooldownSeconds?: number;
	/** Content shown while cooling down. Defaults to `{remaining}s`. */
	cooldownLabel?: (remaining: number) => ReactNode;
};

/**
 * A `Button` that disables itself for `cooldownSeconds` after each click,
 * showing a countdown, to throttle rapid re-triggers. Combine with `disabled`
 * for async pending states.
 */
export function CooldownButton({
	cooldownSeconds = 3,
	cooldownLabel,
	onClick,
	disabled,
	children,
	...props
}: Props) {
	const [remaining, setRemaining] = useState(0);
	const isCoolingDown = remaining > 0;

	useEffect(() => {
		if (!isCoolingDown) {
			return;
		}

		const intervalId = window.setInterval(() => {
			setRemaining((prev) => Math.max(0, prev - 1));
		}, 1000);

		return () => window.clearInterval(intervalId);
	}, [isCoolingDown]);

	const handleClick: NonNullable<Props['onClick']> = (event) => {
		onClick?.(event);

		if (cooldownSeconds > 0) {
			setRemaining(cooldownSeconds);
		}
	};

	return (
		<Button {...props} disabled={disabled || isCoolingDown} onClick={handleClick}>
			{isCoolingDown ? (cooldownLabel?.(remaining) ?? `${remaining}s`) : children}
		</Button>
	);
}
