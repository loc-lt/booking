import { cn } from 'cn';
import { ChevronDownIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import { Button } from '../ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Icon } from './icon';
import type { FilterOption } from './types';

const ALL_VALUE = '__all__';

type Props<TValue extends string = string> = {
	/** Accessible name for the trigger when there's no visible `<Label>` pointing at `id` (e.g. a compact toolbar). */
	ariaLabel?: string;
	className?: string;
	clearLabel: string;
	disabled?: boolean;
	/** Doubles as the trigger's placeholder and the "no filter" option's label. */
	emptyLabel?: ReactNode;
	id?: string;
	onValueChange: (value: TValue | '') => void;
	options: readonly FilterOption<TValue>[];
	value: TValue | '';
};

/**
 * A `Select` with an inline clear (X) button once a value is chosen — the
 * `Select` equivalent of `Search`'s clear affordance. Reused by
 * `DataTableFilters` and any other select-based filter.
 */
export function ClearableSelect<TValue extends string = string>({
	ariaLabel,
	className,
	clearLabel,
	disabled,
	emptyLabel,
	id,
	onValueChange,
	options,
	value,
}: Props<TValue>) {
	return (
		<div className={cn('relative', className)}>
			<Select
				disabled={disabled}
				onValueChange={(nextValue) =>
					onValueChange(nextValue === ALL_VALUE ? '' : (nextValue as TValue))
				}
				value={value || ALL_VALUE}
			>
				<SelectTrigger aria-label={ariaLabel} className='w-full pr-14' hideChevron id={id}>
					{/*
					 * Unlike Radix, Base UI's `Select.Value` doesn't track the matching
					 * item's rendered label on its own — without this render function
					 * it falls back to showing the raw `value` once something is
					 * selected, even though the dropdown itself renders labels fine.
					 */}
					<SelectValue placeholder={emptyLabel}>
						{(selected: string) =>
							selected === ALL_VALUE
								? emptyLabel
								: (options.find((option) => option.value === selected)?.label ?? selected)
						}
					</SelectValue>
				</SelectTrigger>
				<SelectContent>
					{emptyLabel ? <SelectItem value={ALL_VALUE}>{emptyLabel}</SelectItem> : null}
					{options.map((option) => (
						<SelectItem key={option.value} value={option.value}>
							{option.label}
						</SelectItem>
					))}
				</SelectContent>
			</Select>
			{/*
			 * Sits on top of (not inside) the trigger button — the clear button
			 * must stay outside it so clicking clear doesn't also open the
			 * dropdown and so it isn't a `<button>` nested inside a `<button>`.
			 * The chevron is purely decorative (`pointer-events-none`), so
			 * clicks on it fall through to the trigger underneath. The clear
			 * button is always rendered (just `invisible` without a value) so
			 * its reserved space never shifts the chevron/trigger content.
			 */}
			<div className='pointer-events-none absolute top-1/2 right-2 flex -translate-y-1/2 items-center gap-1'>
				<Button
					aria-hidden={!value}
					aria-label={clearLabel}
					className={cn('pointer-events-auto', !value && 'invisible')}
					disabled={disabled || !value}
					onClick={() => onValueChange('')}
					size='icon-sm'
					type='button'
					variant='ghost'
				>
					<Icon name='X' />
				</Button>
				<ChevronDownIcon className='text-muted-foreground size-4' />
			</div>
		</div>
	);
}
