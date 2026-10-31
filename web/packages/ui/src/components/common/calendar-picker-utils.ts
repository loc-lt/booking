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
