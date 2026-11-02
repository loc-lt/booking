import type { Booking } from '@booking-core/api-client';
import type { CalendarViewMode } from '@booking-core/booking-ui';
import { getVisibleDays } from '@booking-core/booking-ui';

function toLocalDate(date: string): Date {
	const [year, month, day] = date.split('-').map(Number);
	return new Date(year ?? 0, (month ?? 1) - 1, day ?? 1);
}

function startOfDayIso(date: Date): string {
	const start = new Date(date);
	start.setHours(0, 0, 0, 0);
	return start.toISOString();
}

function endOfDayIso(date: Date): string {
	const end = new Date(date);
	end.setHours(23, 59, 59, 999);
	return end.toISOString();
}

/**
 * The `listBookings` `from`/`to` window to cover everything `BookingTimeGrid`
 * or `BookingMonthGrid` could show for this reference date and view —
 * padded a week either side for Month view, since its grid shows a few days
 * from the adjacent months too.
 */
export function getQueryRange(
	referenceDate: string,
	viewMode: CalendarViewMode,
): { from: string; to: string } {
	if (viewMode === 'month') {
		const reference = toLocalDate(referenceDate);
		const monthStart = new Date(reference.getFullYear(), reference.getMonth(), 1);
		const monthEnd = new Date(reference.getFullYear(), reference.getMonth() + 1, 0);
		monthStart.setDate(monthStart.getDate() - 7);
		monthEnd.setDate(monthEnd.getDate() + 7);
		return { from: startOfDayIso(monthStart), to: endOfDayIso(monthEnd) };
	}

	const days = getVisibleDays(referenceDate, viewMode);
	const first = days[0] ?? referenceDate;
	const last = days[days.length - 1] ?? referenceDate;
	return { from: startOfDayIso(toLocalDate(first)), to: endOfDayIso(toLocalDate(last)) };
}

function dayKey(iso: string): string {
	const date = new Date(iso);
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

/** Groups bookings by the local calendar day their `start` falls on. */
export function groupBookingsByDay(bookings: Booking[]): Map<string, Booking[]> {
	const byDay = new Map<string, Booking[]>();

	for (const booking of bookings) {
		const key = dayKey(booking.start);
		const existing = byDay.get(key);

		if (existing) {
			existing.push(booking);
		} else {
			byDay.set(key, [booking]);
		}
	}

	return byDay;
}
