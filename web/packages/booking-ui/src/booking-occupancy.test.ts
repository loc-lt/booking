import type { Booking, BookingStatus } from '@booking-core/api-client';
import { describe, expect, it } from 'vitest';
import { findOverlappingBooking, isBlockingBooking } from './booking-occupancy';

function booking(overrides: Partial<Booking> & Pick<Booking, 'start' | 'end' | 'status'>): Booking {
	return {
		id: 'booking-1',
		resourceId: 'resource-1',
		resourceTypeId: 'resource-type-1',
		siteId: 'site-1',
		memberId: 'member-1',
		customFieldValues: {},
		appliedConfig: {
			flowConfigVersion: 1,
			ruleSetVersion: 1,
			confirmation: 'instant',
			checkIn: { required: true, opensMinutesBefore: 15, noShowAfterMinutes: 15 },
			cancellation: { allowedUntilMinutesBefore: 60 },
		},
		history: [],
		createdAt: '2026-11-01T00:00:00+07:00',
		updatedAt: '2026-11-01T00:00:00+07:00',
		...overrides,
	};
}

describe('isBlockingBooking', () => {
	it('holds the slot for awaiting_payment, pending_approval, confirmed, checked_in and completed', () => {
		const blocking: BookingStatus[] = [
			'awaiting_payment',
			'pending_approval',
			'confirmed',
			'checked_in',
			'completed',
		];
		for (const status of blocking) {
			expect(isBlockingBooking(booking({ start: 'x', end: 'y', status }))).toBe(true);
		}
	});

	it('leaves the slot free for expired, rejected, cancelled and no_show', () => {
		const released: BookingStatus[] = ['expired', 'rejected', 'cancelled', 'no_show'];
		for (const status of released) {
			expect(isBlockingBooking(booking({ start: 'x', end: 'y', status }))).toBe(false);
		}
	});
});

describe('findOverlappingBooking', () => {
	const existing = booking({
		start: '2026-11-02T09:00:00+07:00',
		end: '2026-11-02T10:00:00+07:00',
		status: 'confirmed',
	});

	it('returns undefined when there are no bookings', () => {
		const range = { start: '2026-11-02T09:00:00+07:00', end: '2026-11-02T10:00:00+07:00' };
		expect(findOverlappingBooking(range, [])).toBeUndefined();
	});

	it('returns undefined when the range falls entirely outside every booking', () => {
		const range = { start: '2026-11-02T11:00:00+07:00', end: '2026-11-02T12:00:00+07:00' };
		expect(findOverlappingBooking(range, [existing])).toBeUndefined();
	});

	it('does not treat touching boundaries as an overlap', () => {
		// Starts exactly when `existing` ends — a half-open interval, so this is
		// a valid back-to-back booking, not a conflict.
		const backToBack = { start: '2026-11-02T10:00:00+07:00', end: '2026-11-02T11:00:00+07:00' };
		expect(findOverlappingBooking(backToBack, [existing])).toBeUndefined();
	});

	it('finds a booking the range is fully inside', () => {
		const range = { start: '2026-11-02T09:15:00+07:00', end: '2026-11-02T09:45:00+07:00' };
		expect(findOverlappingBooking(range, [existing])).toBe(existing);
	});

	it('finds a booking the range only partially overlaps, on either edge', () => {
		const overlapsStart = { start: '2026-11-02T08:30:00+07:00', end: '2026-11-02T09:30:00+07:00' };
		const overlapsEnd = { start: '2026-11-02T09:30:00+07:00', end: '2026-11-02T10:30:00+07:00' };
		expect(findOverlappingBooking(overlapsStart, [existing])).toBe(existing);
		expect(findOverlappingBooking(overlapsEnd, [existing])).toBe(existing);
	});

	it('ignores a booking whose status has already released the slot, even if the time overlaps', () => {
		const cancelled = booking({
			start: '2026-11-02T09:00:00+07:00',
			end: '2026-11-02T10:00:00+07:00',
			status: 'cancelled',
		});
		const range = { start: '2026-11-02T09:15:00+07:00', end: '2026-11-02T09:45:00+07:00' };
		expect(findOverlappingBooking(range, [cancelled])).toBeUndefined();
	});

	it('returns the first overlapping booking in array order', () => {
		const second = booking({
			id: 'booking-2',
			start: '2026-11-02T09:30:00+07:00',
			end: '2026-11-02T10:30:00+07:00',
			status: 'confirmed',
		});
		const range = { start: '2026-11-02T09:15:00+07:00', end: '2026-11-02T09:45:00+07:00' };
		expect(findOverlappingBooking(range, [existing, second])).toBe(existing);
		expect(findOverlappingBooking(range, [second, existing])).toBe(second);
	});

	it('uses a custom isBlocking predicate instead of the default status set', () => {
		const range = { start: '2026-11-02T09:15:00+07:00', end: '2026-11-02T09:45:00+07:00' };
		expect(findOverlappingBooking(range, [existing], () => false)).toBeUndefined();

		const cancelled = booking({
			start: '2026-11-02T09:00:00+07:00',
			end: '2026-11-02T10:00:00+07:00',
			status: 'cancelled',
		});
		expect(findOverlappingBooking(range, [cancelled], () => true)).toBe(cancelled);
	});
});
