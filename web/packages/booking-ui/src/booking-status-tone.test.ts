import { BookingStatus } from '@booking-core/api-client';
import { describe, expect, it } from 'vitest';
import { bookingStatusTone } from './booking-status-tone';

describe('bookingStatusTone', () => {
	it('tones confirmed and checked_in as "active" — holding the slot, nothing to wait on', () => {
		expect(bookingStatusTone(BookingStatus.confirmed)).toBe('active');
		expect(bookingStatusTone(BookingStatus.checked_in)).toBe('active');
	});

	it('tones awaiting_payment and pending_approval as "pending" — holding the slot, waiting on someone', () => {
		expect(bookingStatusTone(BookingStatus.awaiting_payment)).toBe('pending');
		expect(bookingStatusTone(BookingStatus.pending_approval)).toBe('pending');
	});

	it('tones every released or historical status as "neutral"', () => {
		expect(bookingStatusTone(BookingStatus.completed)).toBe('neutral');
		expect(bookingStatusTone(BookingStatus.expired)).toBe('neutral');
		expect(bookingStatusTone(BookingStatus.rejected)).toBe('neutral');
		expect(bookingStatusTone(BookingStatus.cancelled)).toBe('neutral');
		expect(bookingStatusTone(BookingStatus.no_show)).toBe('neutral');
	});

	it('covers every status the API can return', () => {
		for (const status of Object.values(BookingStatus)) {
			expect(['active', 'pending', 'neutral']).toContain(bookingStatusTone(status));
		}
	});
});
