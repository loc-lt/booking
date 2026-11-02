import type { Booking, FieldDefinition } from '@booking-core/api-client';
import { CustomFieldValuesEditor, type ReferenceOption } from '@booking-core/custom-fields';
import {
	Button,
	DatePicker,
	Icon,
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@booking-core/ui';
import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import type { TimeRange } from './booking-occupancy';
import { findOverlappingBooking, isBlockingBooking } from './booking-occupancy';

export interface BookingCreatePanelProps {
	/** The range seeded by the grid's drag-to-select, as ISO start/end. */
	initialRange: TimeRange;
	/** The resource type's configured fields — drives the custom-field inputs. */
	fields: FieldDefinition[];
	values: Record<string, unknown>;
	onValuesChange: (values: Record<string, unknown>) => void;
	/** Field key -> error message, e.g. from a VALIDATION_FAILED response. */
	fieldErrors?: Record<string, string>;
	referenceOptions?: Record<string, ReferenceOption[]>;
	bookingsByDay: Map<string, Booking[]>;
	/** Defaults to any non-released status (not cancelled/rejected/expired/no_show). */
	isBlocking?: (booking: Booking) => boolean;
	/** Fired as the date/start/end fields are fine-tuned, so the grid's highlight can follow along. */
	onRangeChange: (range: TimeRange) => void;
	onSubmit: (range: TimeRange) => void;
	isSubmitting?: boolean;
	submitLabel?: ReactNode;
	submittingLabel?: ReactNode;
	/** A denial or error banner from the caller's own mutation, e.g. SLOT_TAKEN or BOOKING_DENIED reasons. */
	error?: ReactNode;
	dateLabel?: string;
	startTimeLabel?: string;
	endTimeLabel?: string;
}

const TIME_OPTIONS = Array.from({ length: 96 }, (_, index) => {
	const minutes = index * 15;
	return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
});

function toDateKey(date: Date): string {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

function toTimeKey(date: Date): string {
	return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

function combine(date: string, time: string): string {
	const [year, month, day] = date.split('-').map(Number);
	const [hours, minutes] = time.split(':').map(Number);
	return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1, hours ?? 0, minutes ?? 0).toISOString();
}

function formatDuration(startTime: string, endTime: string): string {
	const toMinutes = (time: string) => {
		const [hours = 0, minutes = 0] = time.split(':').map(Number);
		return hours * 60 + minutes;
	};

	const diff = Math.max(toMinutes(endTime) - toMinutes(startTime), 0);
	return `${Math.floor(diff / 60)}h ${diff % 60}m`;
}

function TimeSelect({
	id,
	minTime,
	onValueChange,
	value,
}: {
	id?: string;
	/** Exclusive lower bound — e.g. the end-time select passes the current start time. */
	minTime?: string;
	onValueChange: (value: string) => void;
	value: string;
}) {
	return (
		<Select onValueChange={(next) => next !== null && onValueChange(next)} value={value}>
			<SelectTrigger className='w-full' id={id}>
				<SelectValue />
			</SelectTrigger>
			<SelectContent className='max-h-64'>
				{TIME_OPTIONS.map((time) => (
					<SelectItem disabled={minTime !== undefined && time <= minTime} key={time} value={time}>
						{time}
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	);
}

/** The time grid's drag-selection turns into this form — fine-tuned time range, date, and the resource type's custom fields. */
export function BookingCreatePanel({
	initialRange,
	fields,
	values,
	onValuesChange,
	fieldErrors,
	referenceOptions,
	bookingsByDay,
	isBlocking = isBlockingBooking,
	onRangeChange,
	onSubmit,
	isSubmitting = false,
	submitLabel = 'Book',
	submittingLabel = 'Booking…',
	error,
	dateLabel = 'Date',
	startTimeLabel = 'Start',
	endTimeLabel = 'End',
}: BookingCreatePanelProps) {
	const [date, setDate] = useState(() => toDateKey(new Date(initialRange.start)));
	const [startTime, setStartTime] = useState(() => toTimeKey(new Date(initialRange.start)));
	const [endTime, setEndTime] = useState(() => toTimeKey(new Date(initialRange.end)));
	const [overlapError, setOverlapError] = useState<string>();

	// Re-dragging on the grid while this panel is already open should only
	// update the time/date fields — a genuinely fresh attempt gets a new
	// instance of this panel instead (the caller remounts it by key).
	useEffect(() => {
		setDate(toDateKey(new Date(initialRange.start)));
		setStartTime(toTimeKey(new Date(initialRange.start)));
		setEndTime(toTimeKey(new Date(initialRange.end)));
	}, [initialRange]);

	// Keep the grid's highlight following the date/start/end fields as the
	// user fine-tunes them here, rather than leaving it frozen at whatever
	// range the original drag produced.
	// biome-ignore lint/correctness/useExhaustiveDependencies: onRangeChange is a stable callback the caller owns, not state to resync on
	useEffect(() => {
		onRangeChange({ start: combine(date, startTime), end: combine(date, endTime) });
	}, [date, startTime, endTime]);

	// The end-time select already excludes times at or before `startTime`, so
	// pushing the start time past the current end time would otherwise leave
	// it holding a value that's no longer a valid option — bump it forward.
	const handleStartTimeChange = (value: string) => {
		setStartTime(value);

		if (endTime <= value) {
			const nextIndex = TIME_OPTIONS.indexOf(value) + 1;
			setEndTime(TIME_OPTIONS[nextIndex] ?? value);
		}
	};

	const handleSubmit = () => {
		setOverlapError(undefined);
		const range = { start: combine(date, startTime), end: combine(date, endTime) };
		const overlapping = findOverlappingBooking(range, bookingsByDay.get(date) ?? [], isBlocking);

		if (overlapping) {
			setOverlapError('This time overlaps an existing booking.');
			return;
		}

		onSubmit(range);
	};

	return (
		<div className='flex flex-col gap-4'>
			<div className='flex items-end gap-2'>
				<div className='flex-1'>
					<span className='mb-1.5 block text-sm font-medium'>{startTimeLabel}</span>
					<TimeSelect onValueChange={handleStartTimeChange} value={startTime} />
				</div>
				<Icon className='text-muted-foreground mb-2.5' name='ArrowRight' />
				<div className='flex-1'>
					<span className='mb-1.5 block text-sm font-medium'>{endTimeLabel}</span>
					<TimeSelect minTime={startTime} onValueChange={setEndTime} value={endTime} />
				</div>
				<span className='text-muted-foreground mb-2.5 shrink-0 text-sm whitespace-nowrap'>
					{formatDuration(startTime, endTime)}
				</span>
			</div>

			<div>
				<span className='mb-1.5 block text-sm font-medium'>{dateLabel}</span>
				<DatePicker clearLabel='Clear' onValueChange={setDate} submitLabel='Apply' value={date} />
			</div>

			<CustomFieldValuesEditor
				errors={fieldErrors}
				fields={fields}
				onChange={onValuesChange}
				referenceOptions={referenceOptions}
				values={values}
			/>

			{overlapError ? <p className='text-destructive text-sm'>{overlapError}</p> : null}
			{error}

			<Button disabled={isSubmitting} onClick={handleSubmit} type='button'>
				{isSubmitting ? submittingLabel : submitLabel}
			</Button>
		</div>
	);
}
