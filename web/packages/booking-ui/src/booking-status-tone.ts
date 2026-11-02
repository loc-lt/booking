import type { Booking } from '@booking-core/api-client';

export type BookingStatusTone = 'active' | 'pending' | 'neutral';

/** Groups the statuses the calendar ever renders (see `isBlockingBooking`) into a look. */
const STATUS_TONES: Record<Booking['status'], BookingStatusTone> = {
	awaiting_payment: 'pending',
	pending_approval: 'pending',
	confirmed: 'active',
	checked_in: 'active',
	completed: 'neutral',
	expired: 'neutral',
	rejected: 'neutral',
	cancelled: 'neutral',
	no_show: 'neutral',
};

export function bookingStatusTone(status: Booking['status']): BookingStatusTone {
	return STATUS_TONES[status];
}
