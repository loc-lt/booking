const timeFormatter = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' });
const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
	month: 'short',
	day: 'numeric',
	hour: 'numeric',
	minute: '2-digit',
});

/** Time only, e.g. "2:00 PM" — for same-day contexts like an availability slot. */
export function formatTime(iso: string): string {
	return timeFormatter.format(new Date(iso));
}

/** Date and time, e.g. "Dec 15, 2:00 PM" — for contexts spanning more than one day. */
export function formatDateTime(iso: string): string {
	return dateTimeFormatter.format(new Date(iso));
}

/** A start–end range, collapsing the end to time-only when both fall on the same day. */
export function formatTimeRange(start: string, end: string): string {
	const startDate = new Date(start);
	const endDate = new Date(end);
	const sameDay = startDate.toDateString() === endDate.toDateString();
	const startLabel = dateTimeFormatter.format(startDate);
	const endLabel = sameDay ? timeFormatter.format(endDate) : dateTimeFormatter.format(endDate);
	return `${startLabel} – ${endLabel}`;
}
