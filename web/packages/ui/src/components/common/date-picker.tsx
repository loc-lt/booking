import { useMemo, useState } from 'react';
import type { Locale } from 'react-day-picker';
import { enUS } from 'react-day-picker/locale';
import { Button } from '../ui/button';
import { Calendar } from '../ui/calendar';
import { Popover, PopoverContent } from '../ui/popover';
import { CalendarPickerTrigger } from './calendar-picker-trigger';
import { buildCalendarDate, formatCalendarDate } from './calendar-picker-utils';
import { Icon } from './icon';

type Props = {
	className?: string;
	clearLabel: string;
	disabled?: boolean;
	id?: string;
	/** Defaults to English (`react-day-picker`'s `enUS`). */
	locale?: Locale;
	onValueChange: (value: string) => void;
	placeholder?: string;
	submitLabel: string;
	value: string;
};

const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

function parseDate(value: string) {
	const match = DATE_PATTERN.exec(value.trim());

	if (!match) {
		return undefined;
	}

	return buildCalendarDate(Number(match[1]), Number(match[2]), Number(match[3]));
}

/** `DateTimePicker`'s date-only counterpart — a calendar with no time-of-day input. */
export function DatePicker({
	className,
	clearLabel,
	disabled,
	id,
	locale = enUS,
	onValueChange,
	placeholder,
	submitLabel,
	value,
}: Props) {
	const selectedDate = useMemo(() => parseDate(value), [value]);
	const [open, setOpen] = useState(false);
	const [draftDate, setDraftDate] = useState<Date | undefined>(selectedDate);
	const [month, setMonth] = useState(() => selectedDate ?? new Date());

	const handleDateSelect = (date: Date | undefined) => {
		if (!date) return;
		setDraftDate(date);
		setMonth(date);
	};

	const handleApply = () => {
		if (!draftDate) {
			return;
		}

		onValueChange(formatCalendarDate(draftDate));
		setOpen(false);
	};

	const handleClear = () => {
		setDraftDate(undefined);
		onValueChange('');
		setOpen(false);
	};

	return (
		<Popover
			onOpenChange={(nextOpen) => {
				if (nextOpen) {
					setDraftDate(selectedDate);

					if (selectedDate) {
						setMonth(selectedDate);
					}
				}

				setOpen(nextOpen);
			}}
			open={open}
		>
			<CalendarPickerTrigger
				className={className}
				clearLabel={clearLabel}
				disabled={disabled}
				id={id}
				onClear={handleClear}
				placeholder={placeholder}
				value={value}
			/>
			{/* `w-auto` (not the popover default `w-72`) so the popover shrinks to
			 * the calendar's own natural width instead of leaving empty space
			 * once there's no time-input row to fill the extra space. */}
			<PopoverContent className='w-auto p-3'>
				<Calendar
					locale={locale}
					mode='single'
					month={month}
					onMonthChange={setMonth}
					onSelect={handleDateSelect}
					selected={draftDate}
				/>

				<div className='mt-3 flex justify-end gap-2'>
					<Button disabled={!draftDate} onClick={handleApply} type='button'>
						<Icon name='Check' />
						{submitLabel}
					</Button>
				</div>
			</PopoverContent>
		</Popover>
	);
}
