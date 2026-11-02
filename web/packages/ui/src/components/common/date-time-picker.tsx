import type { KeyboardEvent } from 'react';
import { useMemo, useState } from 'react';
import type { Locale } from 'react-day-picker';
import { enUS } from 'react-day-picker/locale';
import { Button } from '../ui/button';
import { Calendar } from '../ui/calendar';
import { Input } from '../ui/input';
import { Popover, PopoverContent } from '../ui/popover';
import { CalendarPickerTrigger } from './calendar-picker-trigger';
import { buildCalendarDate, formatCalendarDate, padNumber } from './calendar-picker-utils';
import { Icon } from './icon';

type Props = {
	className?: string;
	clearLabel: string;
	defaultTime?: string;
	disabled?: boolean;
	/** Defaults to `"Time"`. */
	hourLabel?: string;
	id?: string;
	/** Defaults to English (`react-day-picker`'s `enUS`). */
	locale?: Locale;
	/** Defaults to `"Minute"`. */
	minuteLabel?: string;
	onValueChange: (value: string) => void;
	placeholder?: string;
	/** Defaults to `"Second"`. */
	secondLabel?: string;
	submitLabel: string;
	/** Defaults to `"Time"`. */
	timeLabel?: string;
	value: string;
};

const DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?$/;

function normalizeTime(value: string) {
	const [hour = '00', minute = '00', second = '00'] = value.split(':');

	return [
		normalizeTimePart(hour, 23),
		normalizeTimePart(minute, 59),
		normalizeTimePart(second, 59),
	].join(':');
}

function normalizeTimePart(value: string, max: number) {
	const numericValue = Number(value || 0);
	const safeValue = Number.isNaN(numericValue) ? 0 : Math.min(Math.max(numericValue, 0), max);

	return padNumber(safeValue);
}

function getTimeFromValue(value: string, defaultTime: string) {
	const match = DATE_TIME_PATTERN.exec(value.trim());

	if (!match) {
		return defaultTime;
	}

	return normalizeTime([match[4] ?? '00', match[5] ?? '00', match[6] ?? '00'].join(':'));
}

function getTimeParts(value: string, defaultTime: string) {
	const [hour, minute, second] = getTimeFromValue(value, defaultTime).split(':');

	return {
		hour,
		minute,
		second,
	};
}

function parseDateTime(value: string) {
	const match = DATE_TIME_PATTERN.exec(value.trim());

	if (!match) {
		return undefined;
	}

	return buildCalendarDate(Number(match[1]), Number(match[2]), Number(match[3]));
}

export function DateTimePicker({
	className,
	clearLabel,
	defaultTime = '00:00:00',
	disabled,
	hourLabel = 'Hour',
	id,
	locale = enUS,
	minuteLabel = 'Minute',
	onValueChange,
	placeholder,
	secondLabel = 'Second',
	submitLabel,
	timeLabel = 'Time',
	value,
}: Props) {
	const selectedDate = useMemo(() => parseDateTime(value), [value]);
	const selectedTimeParts = useMemo(() => getTimeParts(value, defaultTime), [defaultTime, value]);
	const [open, setOpen] = useState(false);
	const [draftDate, setDraftDate] = useState<Date | undefined>(selectedDate);
	const [draftTime, setDraftTime] = useState(selectedTimeParts);
	const [month, setMonth] = useState(() => selectedDate ?? new Date());

	const syncDraftFromValue = () => {
		setDraftDate(selectedDate);
		setDraftTime(selectedTimeParts);

		if (selectedDate) {
			setMonth(selectedDate);
		}
	};

	const handleDateSelect = (date: Date | undefined) => {
		if (!date) return;
		setDraftDate(date);
		setMonth(date);
	};

	const handleTimePartChange = (key: keyof typeof draftTime, nextValue: string) => {
		setDraftTime((currentTime) => ({
			...currentTime,
			[key]: nextValue.replace(/\D/g, '').slice(0, 2),
		}));
	};

	const handleApply = () => {
		if (!draftDate) {
			return;
		}

		onValueChange(
			`${formatCalendarDate(draftDate)} ${normalizeTime([draftTime.hour, draftTime.minute, draftTime.second].join(':'))}`,
		);
		setOpen(false);
	};

	const handleTimeInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
		if (event.key !== 'Enter') {
			return;
		}

		event.preventDefault();
		handleApply();
	};

	const handleClear = () => {
		setDraftDate(undefined);
		setDraftTime(getTimeParts('', defaultTime));
		onValueChange('');
		setOpen(false);
	};

	return (
		<Popover
			onOpenChange={(nextOpen) => {
				if (nextOpen) {
					syncDraftFromValue();
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
			 * the calendar's own natural width instead of leaving empty space to
			 * its right. `collisionAvoidance={{ side: 'none' }}` keeps it below
			 * the trigger always — like `DatePicker` — instead of flipping to a
			 * side when there isn't room below; this popup is taller (calendar
			 * + time row), so it hit that flip more easily. */}
			<PopoverContent className='w-auto p-3' collisionAvoidance={{ side: 'none' }}>
				<Calendar
					locale={locale}
					mode='single'
					month={month}
					onMonthChange={setMonth}
					onSelect={handleDateSelect}
					selected={draftDate}
				/>

				<div className='mt-3 grid gap-1.5 border-t pt-3'>
					<div className='text-xs/relaxed font-medium'>{timeLabel}</div>
					{/*
					 * `justify-items-center` + a fixed `w-14` on each `Input` below —
					 * without an explicit width, a plain `<input>`'s intrinsic size
					 * defaults to roughly 20 characters regardless of `maxLength`,
					 * so these 2-digit fields rendered far wider than their content
					 * needs. The `1fr` columns still spread the three fields evenly
					 * across the calendar's width above them; only the input boxes
					 * themselves are now small.
					 */}
					<div className='grid grid-cols-[1fr_auto_1fr_auto_1fr] items-center justify-items-center gap-1'>
						<Input
							aria-label={hourLabel}
							className='w-14 text-center'
							inputMode='numeric'
							maxLength={2}
							onChange={(event) => handleTimePartChange('hour', event.target.value)}
							onKeyDown={handleTimeInputKeyDown}
							placeholder='HH'
							value={draftTime.hour}
						/>
						<span className='text-muted-foreground text-center'>:</span>
						<Input
							aria-label={minuteLabel}
							className='w-14 text-center'
							inputMode='numeric'
							maxLength={2}
							onChange={(event) => handleTimePartChange('minute', event.target.value)}
							onKeyDown={handleTimeInputKeyDown}
							placeholder='mm'
							value={draftTime.minute}
						/>
						<span className='text-muted-foreground text-center'>:</span>
						<Input
							aria-label={secondLabel}
							className='w-14 text-center'
							inputMode='numeric'
							maxLength={2}
							onChange={(event) => handleTimePartChange('second', event.target.value)}
							onKeyDown={handleTimeInputKeyDown}
							placeholder='ss'
							value={draftTime.second}
						/>
					</div>
				</div>

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
