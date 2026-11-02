import type { Booking } from '@booking-core/api-client';

export interface TimeRange {
	start: string;
	end: string;
}

/** Statuses that hold the slot — everything else (cancelled, rejected, expired, no_show) left it free. */
const BLOCKING_STATUSES: ReadonlySet<Booking['status']> = new Set([
	'awaiting_payment',
	'pending_approval',
	'confirmed',
	'checked_in',
	'completed',
]);

/** Defaults to treating any non-terminal-released status as occupying its slot. */
export function isBlockingBooking(booking: Booking): boolean {
	return BLOCKING_STATUSES.has(booking.status);
}

/** The first booking (by the given predicate) that overlaps `range`, or `undefined`. */
export function findOverlappingBooking(
	range: TimeRange,
	bookings: Booking[],
	isBlocking: (booking: Booking) => boolean = isBlockingBooking,
): Booking | undefined {
	const start = new Date(range.start).getTime();
	const end = new Date(range.end).getTime();

	return bookings.find((booking) => {
		if (!isBlocking(booking)) {
			return false;
		}

		const bookingStart = new Date(booking.start).getTime();
		const bookingEnd = new Date(booking.end).getTime();
		return start < bookingEnd && end > bookingStart;
	});
}
