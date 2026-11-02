import type { Booking } from '@booking-core/api-client';
import { cn } from 'cn';
import type { ReactNode, WheelEvent } from 'react';
import { useRef } from 'react';
import { bookingStatusTone } from './booking-status-tone';
import { formatTime } from './format-date-time';

/** Matches the time grid's per-status tiles (`BookingTimeGrid`) at pill scale. */
const BOOKING_PILL_TONE_CLASSES: Record<ReturnType<typeof bookingStatusTone>, string> = {
	active: 'bg-primary/10 text-primary hover:bg-primary/20',
	pending: 'bg-secondary text-secondary-foreground hover:bg-secondary/70',
	neutral: 'bg-muted text-muted-foreground hover:bg-muted/70',
};

export interface BookingMonthGridProps {
	onNavigateMonth: (direction: 1 | -1) => void;
	onSelectBooking: (booking: Booking) => void;
	/** Clicking anywhere in a day's cell outside its booking pills, e.g. to drill into that day for booking. Omit to make the grid look-only. */
	onSelectDay?: (day: string) => void;
	/** Any date within the month to display ('YYYY-MM-DD') — only its year/month matter. */
	referenceDate: string;
	bookingsByDay: Map<string, Booking[]>;
	/** Full control over one day's booking pill, e.g. to show a tenant's title field. */
	renderBookingPill?: (booking: Booking) => ReactNode;
	maxPillsPerDay?: number;
	weekdayLabels?: string[];
	moreLabel?: (count: number) => string;
}

const DEFAULT_WEEKDAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DEFAULT_MAX_PILLS_PER_DAY = 3;
// A single mouse-wheel notch reports a `deltaY` around 100, but trackpads emit
// a stream of much smaller deltas during one inertial swipe — ignore anything
// below this so a light touch doesn't flip the month, and rate-limit with a
// cooldown so one swipe doesn't page through several months at once.
const WHEEL_NAVIGATION_THRESHOLD = 12;
const WHEEL_NAVIGATION_COOLDOWN_MS = 350;

function toLocalDate(date: string): Date {
	const [year, month, day] = date.split('-').map(Number);
	return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1);
}

function toDateKey(date: Date): string {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

function startOfWeek(date: Date): Date {
	// Monday-based, matching `BookingTimeGrid`'s week.
	const daysSinceMonday = (date.getDay() + 6) % 7;
	const start = new Date(date);
	start.setDate(start.getDate() - daysSinceMonday);
	return start;
}

function buildMonthDays(referenceDate: string): string[] {
	const reference = toLocalDate(referenceDate);
	const monthStart = new Date(reference.getFullYear(), reference.getMonth(), 1);
	const monthEnd = new Date(reference.getFullYear(), reference.getMonth() + 1, 0);
	const gridStart = startOfWeek(monthStart);
	const gridEnd = startOfWeek(monthEnd);
	gridEnd.setDate(gridEnd.getDate() + 6);

	const days: string[] = [];
	for (
		const cursor = new Date(gridStart);
		cursor <= gridEnd;
		cursor.setDate(cursor.getDate() + 1)
	) {
		days.push(toDateKey(cursor));
	}

	return days;
}

/** Read-only month overview — each day lists its bookings as clickable pills. */
export function BookingMonthGrid({
	onNavigateMonth,
	onSelectBooking,
	onSelectDay,
	referenceDate,
	bookingsByDay,
	renderBookingPill,
	maxPillsPerDay = DEFAULT_MAX_PILLS_PER_DAY,
	weekdayLabels = DEFAULT_WEEKDAY_LABELS,
	moreLabel = (count) => `+${count} more`,
}: BookingMonthGridProps) {
	const currentMonth = referenceDate.slice(0, 7);
	const today = toDateKey(new Date());
	const days = buildMonthDays(referenceDate);
	const rowCount = days.length / 7;
	const lastWheelNavigationRef = useRef(0);

	const handleWheel = (event: WheelEvent<HTMLDivElement>) => {
		if (Math.abs(event.deltaY) < WHEEL_NAVIGATION_THRESHOLD) return;

		const now = Date.now();
		if (now - lastWheelNavigationRef.current < WHEEL_NAVIGATION_COOLDOWN_MS) return;

		lastWheelNavigationRef.current = now;
		onNavigateMonth(event.deltaY > 0 ? 1 : -1);
	};

	return (
		<div className='flex min-h-0 flex-1 flex-col' onWheel={handleWheel}>
			<div className='grid shrink-0 grid-cols-7 border-b'>
				{weekdayLabels.map((label) => (
					<div className='text-muted-foreground py-2 text-center text-xs' key={label}>
						{label}
					</div>
				))}
			</div>
			<div
				className='grid min-h-0 flex-1 grid-cols-7 overflow-y-auto'
				style={{ gridTemplateRows: `repeat(${rowCount}, minmax(6rem, 1fr))` }}
			>
				{days.map((day) => {
					const isCurrentMonth = day.startsWith(currentMonth);
					const isToday = day === today;
					const dayBookings = [...(bookingsByDay.get(day) ?? [])].sort((a, b) =>
						a.start.localeCompare(b.start),
					);
					const visible = dayBookings.slice(0, maxPillsPerDay);
					const overflowCount = dayBookings.length - visible.length;

					return (
						<div
							className={cn(
								'flex flex-col gap-1 border-r border-b p-1.5 last:border-r-0',
								!isCurrentMonth && 'bg-muted/30',
								onSelectDay && 'hover:bg-muted/50 cursor-pointer',
							)}
							key={day}
							onClick={() => onSelectDay?.(day)}
						>
							<span
								className={cn(
									'flex size-5 shrink-0 items-center justify-center self-end rounded-full text-xs',
									isCurrentMonth ? undefined : 'text-muted-foreground',
									isToday && 'bg-primary text-primary-foreground',
								)}
							>
								{Number(day.slice(8, 10))}
							</span>
							{visible.map((booking) => (
								<button
									className={cn(
										'w-full min-w-0 truncate rounded px-1 py-0.5 text-left text-xs',
										BOOKING_PILL_TONE_CLASSES[bookingStatusTone(booking.status)],
									)}
									key={booking.id}
									onClick={(event) => {
										event.stopPropagation();
										onSelectBooking(booking);
									}}
									type='button'
								>
									{renderBookingPill ? renderBookingPill(booking) : formatTime(booking.start)}
								</button>
							))}
							{overflowCount > 0 ? (
								<span className='text-muted-foreground text-xs'>{moreLabel(overflowCount)}</span>
							) : null}
						</div>
					);
				})}
			</div>
		</div>
	);
}
