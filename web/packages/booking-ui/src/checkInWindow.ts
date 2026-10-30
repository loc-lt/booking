import type { Booking } from '@booking-core/api-client';

/** Whether a booking can be checked in right now: confirmed, and within its check-in window. */
export function isCheckInOpen(booking: Booking, now: Date): boolean {
	if (booking.status !== 'confirmed') {
		return false;
	}

	const { opensMinutesBefore, noShowAfterMinutes } = booking.appliedConfig.checkIn;
	const start = new Date(booking.start).getTime();
	const opensAt = start - opensMinutesBefore * 60_000;
	const closesAt = start + noShowAfterMinutes * 60_000;
	const nowMillis = now.getTime();

	return nowMillis >= opensAt && nowMillis < closesAt;
}
