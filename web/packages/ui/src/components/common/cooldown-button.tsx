import { cn } from 'cn';
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

	const resolveCooldownLabel = (value: number) => cooldownLabel?.(value) ?? `${value}s`;

	return (
		<Button {...props} disabled={disabled || isCoolingDown} onClick={handleClick}>
			{/*
			 * `children` and the cooldown label are stacked in the same grid
			 * cell (overlapping, one hidden via `invisible`) instead of swapped
			 * in and out — that way the button's intrinsic size is always the
			 * larger of the two, so starting (or progressing through) the
			 * cooldown never shrinks or grows the button. The third, always-
			 * invisible span reserves width for the longest countdown digit
			 * count up front (e.g. "10s"), so the button doesn't resize again
			 * when `remaining` drops from double to single digits mid-cooldown.
			 */}
			<span className='grid'>
				<span className={cn('col-start-1 row-start-1', isCoolingDown && 'invisible')}>
					{children}
				</span>
				<span className={cn('col-start-1 row-start-1', !isCoolingDown && 'invisible')}>
					{resolveCooldownLabel(remaining)}
				</span>
				<span aria-hidden className='invisible col-start-1 row-start-1'>
					{resolveCooldownLabel(cooldownSeconds)}
				</span>
			</span>
		</Button>
	);
}
