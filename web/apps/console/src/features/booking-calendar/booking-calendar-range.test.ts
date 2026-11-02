import type { Booking } from '@booking-core/api-client';
import { describe, expect, it } from 'vitest';
import { getQueryRange, groupBookingsByDay } from './booking-calendar-range';

// Built the same way the module under test builds its own boundaries — local
// year/month/day/time, then `toISOString()` — so these assertions hold
// regardless of the machine's timezone running the suite.
function startOfDay(year: number, month: number, day: number): string {
	return new Date(year, month - 1, day, 0, 0, 0, 0).toISOString();
}

function endOfDay(year: number, month: number, day: number): string {
	return new Date(year, month - 1, day, 23, 59, 59, 999).toISOString();
}

describe('getQueryRange', () => {
	it('covers just the one day, start to end, for "day"', () => {
		expect(getQueryRange('2026-11-05', 'day')).toEqual({
			from: startOfDay(2026, 11, 5),
			to: endOfDay(2026, 11, 5),
		});
	});

	it('covers Monday through Sunday of the containing week for "week", regardless of which weekday is passed in', () => {
		const expected = { from: startOfDay(2026, 11, 2), to: endOfDay(2026, 11, 8) };
		expect(getQueryRange('2026-11-05', 'week')).toEqual(expected);
		expect(getQueryRange('2026-11-02', 'week')).toEqual(expected);
		expect(getQueryRange('2026-11-08', 'week')).toEqual(expected);
	});

	it('pads 7 days either side of the month for "month", to cover the grid\'s adjacent-month days', () => {
		// November 2026: 1st is a Sunday, 30th is a Monday.
		expect(getQueryRange('2026-11-15', 'month')).toEqual({
			from: startOfDay(2026, 10, 25),
			to: endOfDay(2026, 12, 7),
		});
	});
});

function booking(id: string, start: string): Booking {
	return {
		id,
		resourceId: 'resource-1',
		resourceTypeId: 'resource-type-1',
		siteId: 'site-1',
		memberId: 'member-1',
		start,
		end: start,
		status: 'confirmed',
		customFieldValues: {},
		appliedConfig: {
			flowConfigVersion: 1,
			ruleSetVersion: 1,
			confirmation: 'instant',
			checkIn: { required: true, opensMinutesBefore: 15, noShowAfterMinutes: 15 },
			cancellation: { allowedUntilMinutesBefore: 60 },
		},
		history: [],
		createdAt: start,
		updatedAt: start,
	};
}

describe('groupBookingsByDay', () => {
	it('returns an empty map for no bookings', () => {
		expect(groupBookingsByDay([])).toEqual(new Map());
	});

	it('groups bookings that start on the same local day under one key', () => {
		const morning = booking('a', '2026-11-02T09:00:00+07:00');
		const afternoon = booking('b', '2026-11-02T14:00:00+07:00');
		const grouped = groupBookingsByDay([morning, afternoon]);
		expect(grouped.get('2026-11-02')).toEqual([morning, afternoon]);
		expect(grouped.size).toBe(1);
	});

	it('keeps bookings on different days under separate keys', () => {
		const first = booking('a', '2026-11-02T09:00:00+07:00');
		const second = booking('b', '2026-11-03T09:00:00+07:00');
		const grouped = groupBookingsByDay([first, second]);
		expect(grouped.get('2026-11-02')).toEqual([first]);
		expect(grouped.get('2026-11-03')).toEqual([second]);
	});

	it("preserves each day's input order", () => {
		const later = booking('a', '2026-11-02T14:00:00+07:00');
		const earlier = booking('b', '2026-11-02T09:00:00+07:00');
		// Passed in "later, earlier" order — grouping must not re-sort.
		expect(groupBookingsByDay([later, earlier]).get('2026-11-02')).toEqual([later, earlier]);
	});
});
