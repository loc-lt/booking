export function padNumber(value: number) {
	return String(value).padStart(2, '0');
}

/** Formats a `Date` as `YYYY-MM-DD` using its local calendar fields (not UTC), so it matches whatever the user picked on-screen. */
export function formatCalendarDate(date: Date) {
	return [date.getFullYear(), padNumber(date.getMonth() + 1), padNumber(date.getDate())].join('-');
}

/**
 * Builds a `Date` from a 1-indexed year/month/day, returning `undefined` if
 * the combination doesn't round-trip (e.g. day 30 in February) — `Date`
 * itself silently rolls invalid dates over into the next month instead of
 * rejecting them, so callers need this check to treat those as unparsed.
 */
export function buildCalendarDate(year: number, month: number, day: number): Date | undefined {
	const date = new Date(year, month - 1, day);

	if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
		return undefined;
	}

	return date;
}

const CALENDAR_DATE_TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?$/;

/**
 * Parses `DateTimePicker`'s `"YYYY-MM-DD"` or `"YYYY-MM-DD HH:MM[:SS]"`
 * value (local time) into a `Date`, or `undefined` if it doesn't match or
 * round-trip. The single source of truth for that format — reuse this
 * instead of hand-rolling another regex when converting it to/from
 * something else (e.g. an ISO string for storage).
 */
export function parseCalendarDateTime(value: string): Date | undefined {
	const match = CALENDAR_DATE_TIME_PATTERN.exec(value.trim());

	if (!match) {
		return undefined;
	}

	const [, year, month, day, hour = '0', minute = '0', second = '0'] = match;
	const date = buildCalendarDate(Number(year), Number(month), Number(day));

	if (!date) {
		return undefined;
	}

	date.setHours(Number(hour), Number(minute), Number(second), 0);

	return date;
}
