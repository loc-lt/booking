import { cn } from 'cn';
import { type ComponentProps, forwardRef } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Icon } from './icon';

type Props = Omit<ComponentProps<typeof Input>, 'value'> & {
	clearLabel: string;
	/** Called when the clear button is clicked — callers decide what "empty" means (`setValue('')`, `onChange(undefined)`, RHF's `setValue`, etc.). */
	onClear: () => void;
	value?: string;
};

/**
 * An `Input` with an inline clear (X) button once it has a value — the
 * `Input` equivalent of `ClearableSelect`'s and `Search`'s clear affordance.
 */
export const ClearableInput = forwardRef<HTMLInputElement, Props>(function ClearableInput(
	{ className, clearLabel, disabled, onClear, value, ...props },
	ref,
) {
	const hasValue = Boolean(value);

	return (
		<div className={cn('relative', className)}>
			{/*
			 * `pr-8` always, not just when `hasValue` — in a container that
			 * doesn't give this input an explicit width (e.g. a plain flex
			 * row), an `<input>`'s own rendered width is its intrinsic size
			 * plus its padding. Toggling the padding on and off therefore
			 * toggled the input's actual width too, not just the room inside
			 * it, shrinking it the moment the clear button disappeared.
			 */}
			<Input className='pr-8' disabled={disabled} ref={ref} value={value} {...props} />
			{hasValue ? (
				// Centering transform lives on this wrapper, not the Button itself —
				// Button's own `active:translate-y-px` would otherwise overwrite the
				// `-translate-y-1/2` offset on click, since both set the same
				// `--tw-translate-y` custom property, making the button jump out of
				// the input instead of nudging down by a pixel.
				<div className='absolute top-1/2 right-1 -translate-y-1/2'>
					<Button
						aria-label={clearLabel}
						disabled={disabled}
						onClick={onClear}
						size='icon-sm'
						type='button'
						variant='ghost'
					>
						<Icon name='X' />
					</Button>
				</div>
			) : null}
		</div>
	);
});
