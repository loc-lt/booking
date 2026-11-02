import { describe, expect, it } from 'vitest';
import { getVisibleDays, navigateCalendar, startOfWeek } from './calendar-navigation';

describe('startOfWeek', () => {
	it('returns the same date when it is already Monday', () => {
		expect(startOfWeek('2026-11-02')).toBe('2026-11-02');
	});

	it('returns the preceding Monday for a mid-week date', () => {
		expect(startOfWeek('2026-11-05')).toBe('2026-11-02');
	});

	it('returns the preceding Monday for a Sunday', () => {
		expect(startOfWeek('2026-11-08')).toBe('2026-11-02');
	});

	it('crosses a month boundary', () => {
		expect(startOfWeek('2026-12-01')).toBe('2026-11-30');
	});
});

describe('getVisibleDays', () => {
	it('returns exactly the reference date for "day"', () => {
		expect(getVisibleDays('2026-11-05', 'day')).toEqual(['2026-11-05']);
	});

	it('returns the 7 days of the week, Monday first, for "week"', () => {
		expect(getVisibleDays('2026-11-05', 'week')).toEqual([
			'2026-11-02',
			'2026-11-03',
			'2026-11-04',
			'2026-11-05',
			'2026-11-06',
			'2026-11-07',
			'2026-11-08',
		]);
	});

	it('anchors to the same week regardless of which day of it is passed in', () => {
		expect(getVisibleDays('2026-11-02', 'week')).toEqual(getVisibleDays('2026-11-08', 'week'));
	});

	it('falls through to the week range for "month" — only "day" is special-cased', () => {
		expect(getVisibleDays('2026-11-05', 'month')).toEqual(getVisibleDays('2026-11-05', 'week'));
	});
});

describe('navigateCalendar', () => {
	it('steps by one day in "day" mode, crossing a month boundary', () => {
		expect(navigateCalendar('2026-11-30', 'day', 1)).toBe('2026-12-01');
		expect(navigateCalendar('2026-12-01', 'day', -1)).toBe('2026-11-30');
	});

	it('steps by 7 days in "week" mode', () => {
		expect(navigateCalendar('2026-11-05', 'week', 1)).toBe('2026-11-12');
		expect(navigateCalendar('2026-11-05', 'week', -1)).toBe('2026-10-29');
	});

	it('steps by one calendar month in "month" mode, crossing a year boundary', () => {
		expect(navigateCalendar('2026-12-15', 'month', 1)).toBe('2027-01-15');
		expect(navigateCalendar('2027-01-15', 'month', -1)).toBe('2026-12-15');
	});

	it('rolls over into the following month when the day-of-month does not exist there (native Date behaviour)', () => {
		// 2026 is not a leap year, so February has 28 days — Jan 31 + 1 month
		// overflows to March 3rd instead of clamping to Feb 28th. Documented
		// here so a future fix (clamping) is a deliberate change, not a surprise.
		expect(navigateCalendar('2026-01-31', 'month', 1)).toBe('2026-03-03');
	});
});
