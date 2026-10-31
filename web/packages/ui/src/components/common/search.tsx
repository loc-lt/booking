import { cn } from 'cn';
import { useEffect, useRef, useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Icon } from './icon';

type Props = {
	className?: string;
	/** Defaults to `"Clear"`. */
	clearLabel?: string;
	debounceDuration?: number;
	defaultValue?: string;
	disabled?: boolean;
	id?: string;
	onValueChange?: (value: string) => void;
	/** Defaults to `"Search"`. */
	placeholder?: string;
	value?: string;
};

export function Search({
	className,
	clearLabel = 'Clear',
	debounceDuration = 500,
	defaultValue = '',
	disabled,
	id,
	onValueChange,
	placeholder = 'Search',
	value,
}: Props) {
	const [internalState, setInternalState] = useState({
		controlledValue: value,
		shouldDebounce: false,
		value: value ?? defaultValue,
	});
	const onValueChangeRef = useRef(onValueChange);

	if (value !== undefined && value !== internalState.controlledValue) {
		setInternalState({
			controlledValue: value,
			shouldDebounce: false,
			value,
		});
	}

	const internalValue =
		value !== undefined && value !== internalState.controlledValue ? value : internalState.value;

	useEffect(() => {
		onValueChangeRef.current = onValueChange;
	}, [onValueChange]);

	useEffect(() => {
		if (!internalState.shouldDebounce) {
			return;
		}

		const timeout = setTimeout(() => {
			onValueChangeRef.current?.(internalValue.trim());
		}, debounceDuration);

		return () => clearTimeout(timeout);
	}, [internalValue, debounceDuration, internalState.shouldDebounce]);

	const handleValueChange = (nextValue: string) => {
		setInternalState({
			controlledValue: value,
			shouldDebounce: true,
			value: nextValue,
		});
	};

	const handleClear = () => {
		setInternalState({
			controlledValue: value,
			shouldDebounce: false,
			value: '',
		});
		onValueChangeRef.current?.('');
	};

	return (
		<div className={cn('relative', className)}>
			<Icon className='absolute top-1/2 left-2 -translate-y-1/2' name='Search' />
			<Input
				className='pr-8 pl-8'
				disabled={disabled}
				id={id}
				onChange={(event) => handleValueChange(event.target.value)}
				placeholder={placeholder}
				value={internalValue}
			/>
			{internalValue ? (
				// Centering transform lives on this wrapper, not the Button itself —
				// Button's own `active:translate-y-px` would otherwise overwrite the
				// `-translate-y-1/2` offset on click, since both set the same
				// `--tw-translate-y` custom property, making the button jump out of
				// the input instead of nudging down by a pixel.
				<div className='absolute top-1/2 right-1 -translate-y-1/2'>
					<Button
						aria-label={clearLabel}
						disabled={disabled}
						onClick={handleClear}
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
