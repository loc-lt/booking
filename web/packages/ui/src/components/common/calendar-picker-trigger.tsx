import { cn } from 'cn';
import { Button } from '../ui/button';
import { PopoverTrigger } from '../ui/popover';
import { Icon } from './icon';

type Props = {
	className?: string;
	clearLabel: string;
	disabled?: boolean;
	id?: string;
	onClear: () => void;
	placeholder?: string;
	value: string;
};

/**
 * Shared trigger button (+ inline clear affordance once a value is set) for
 * `DatePicker`/`DateTimePicker` — must render inside a `Popover`, since it
 * wraps a `PopoverTrigger`.
 */
export function CalendarPickerTrigger({
	className,
	clearLabel,
	disabled,
	id,
	onClear,
	placeholder,
	value,
}: Props) {
	return (
		<div className='relative'>
			<PopoverTrigger
				render={
					<Button
						className={cn(
							'bg-input/20 dark:bg-input/30 h-8 w-full justify-start gap-2 px-2 text-left font-normal',
							value && 'pr-8',
							!value && 'text-muted-foreground',
							className,
						)}
						disabled={disabled}
						id={id}
						type='button'
						variant='outline'
					>
						<Icon name='Calendar' />
						<span className='truncate'>{value || placeholder}</span>
					</Button>
				}
			/>
			{value ? (
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
}
