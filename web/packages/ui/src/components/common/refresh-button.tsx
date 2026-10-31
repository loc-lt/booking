import { CooldownButton } from './cooldown-button';
import { Icon } from './icon';

type Props = {
	disabled?: boolean;
	/** Defaults to `"Refresh"`. */
	label?: string;
	onClick: () => void;
	/** Show the label next to the icon/countdown. Defaults to `true` — set `false` for an icon+countdown-only compact button. */
	showLabel?: boolean;
};

const COOLDOWN_SECONDS = 3;

// Icon and countdown share one fixed-width slot (rather than sitting side by
// side) — swapping which one renders there never changes the slot's own
// size, so the button's width stays constant whether it's showing the icon
// or "3s"/"2s"/"1s".
function RefreshLabel({
	label,
	remaining,
	showLabel,
}: {
	label: string;
	remaining: number;
	showLabel: boolean;
}) {
	return (
		<>
			<span className='inline-flex h-4 w-5 shrink-0 items-center justify-center'>
				{remaining > 0 ? <span className='text-xs'>{remaining}s</span> : <Icon name='RefreshCw' />}
			</span>
			{showLabel ? <> {label}</> : null}
		</>
	);
}

/**
 * Standard "Refresh" action shared by every data-table card. While cooling
 * down, the icon is replaced by a live countdown ("3s" → "2s" → "1s") in the
 * same fixed-size slot, so the button's width never shifts the toolbar.
 */
export function RefreshButton({ disabled, label = 'Refresh', onClick, showLabel = true }: Props) {
	return (
		<CooldownButton
			aria-label={showLabel ? undefined : label}
			cooldownLabel={(remaining) => (
				<RefreshLabel label={label} remaining={remaining} showLabel={showLabel} />
			)}
			cooldownSeconds={COOLDOWN_SECONDS}
			disabled={disabled}
			onClick={onClick}
			variant='outline'
		>
			<RefreshLabel label={label} remaining={0} showLabel={showLabel} />
		</CooldownButton>
	);
}
