export type CalendarViewMode = 'day' | 'week' | 'month';

/** Parses a 'YYYY-MM-DD' key as a local-midnight `Date` (never UTC — avoids off-by-one days). */
export function toLocalDate(date: string): Date {
	const [year, month, day] = date.split('-').map(Number);
	return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1);
}

/** The inverse of `toLocalDate` — a `Date`'s own 'YYYY-MM-DD', in local time. */
export function toDateKey(date: Date): string {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

/** Monday for the week containing `date` — the grid's week always starts on Monday. */
export function startOfWeek(date: string): string {
	const parsed = toLocalDate(date);
	const daysSinceMonday = (parsed.getDay() + 6) % 7;
	parsed.setDate(parsed.getDate() - daysSinceMonday);
	return toDateKey(parsed);
}

/** The days `BookingTimeGrid` should show for a view mode: one day, or Monday–Sunday. */
export function getVisibleDays(referenceDate: string, viewMode: CalendarViewMode): string[] {
	if (viewMode === 'day') {
		return [referenceDate];
	}

	const start = toLocalDate(startOfWeek(referenceDate));
	return Array.from({ length: 7 }, (_, index) => {
		const day = new Date(start);
		day.setDate(day.getDate() + index);
		return toDateKey(day);
	});
}

/** Steps `referenceDate` forward or back by one unit of `viewMode` (day, week or month). */
export function navigateCalendar(
	referenceDate: string,
	viewMode: CalendarViewMode,
	direction: 1 | -1,
): string {
	const date = toLocalDate(referenceDate);

	if (viewMode === 'month') {
		date.setMonth(date.getMonth() + direction);
	} else if (viewMode === 'week') {
		date.setDate(date.getDate() + direction * 7);
	} else {
		date.setDate(date.getDate() + direction);
	}

	return toDateKey(date);
}
