import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { bookingsScenarioHandlers, resetBookingsScenario } from './bookingsStore';

const MEETING_ROOM_A_ID = '0193f4c4-3e7f-7a7c-ab6e-5d3f0a9b8c7d';
const SEEDED_BOOKING_ID = '0193f4c6-5a91-7c9e-cd80-7f5b2c1d0e9f';

const server = setupServer(...bookingsScenarioHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
beforeEach(() => resetBookingsScenario());

describe('bookingsScenarioHandlers', () => {
	it('409s with SLOT_TAKEN when the resource is already booked for that time', async () => {
		const response = await fetch('http://localhost/bookings', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				resourceId: MEETING_ROOM_A_ID,
				start: '2026-12-15T09:00:00+07:00',
				end: '2026-12-15T09:30:00+07:00',
			}),
		});

		expect(response.status).toBe(409);
		const body = await response.json();
		expect(body.code).toBe('SLOT_TAKEN');
	});

	it('422s with BOOKING_DENIED and reasons when a rule blocks the request', async () => {
		const response = await fetch('http://localhost/bookings', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				resourceId: MEETING_ROOM_A_ID,
				start: '2026-12-15T07:00:00+07:00',
				end: '2026-12-15T07:30:00+07:00',
			}),
		});

		expect(response.status).toBe(422);
		const body = await response.json();
		expect(body.code).toBe('BOOKING_DENIED');
		expect(body.reasons).toEqual([
			{ ruleId: 'no-early-bookings', message: 'This resource cannot be booked before 9am.' },
		]);
	});

	it('creates a confirmed booking for a free slot', async () => {
		const response = await fetch('http://localhost/bookings', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				resourceId: MEETING_ROOM_A_ID,
				start: '2026-12-15T10:00:00+07:00',
				end: '2026-12-15T10:30:00+07:00',
			}),
		});

		expect(response.status).toBe(201);
		const body = await response.json();
		expect(body.status).toBe('confirmed');
		expect(body.history).toHaveLength(1);
	});

	it('409s with INVALID_TRANSITION when checking in a booking that is not confirmed', async () => {
		await fetch(`http://localhost/bookings/${SEEDED_BOOKING_ID}/check-in`, { method: 'POST' });
		const response = await fetch(`http://localhost/bookings/${SEEDED_BOOKING_ID}/check-in`, {
			method: 'POST',
		});

		expect(response.status).toBe(409);
		const body = await response.json();
		expect(body.code).toBe('INVALID_TRANSITION');
	});

	it('moves a booking to checked_in and records the transition in history', async () => {
		const response = await fetch(`http://localhost/bookings/${SEEDED_BOOKING_ID}/check-in`, {
			method: 'POST',
		});

		expect(response.status).toBe(200);
		const body = await response.json();
		expect(body.status).toBe('checked_in');
		expect(body.history.at(-1)).toMatchObject({ fromStatus: 'confirmed', toStatus: 'checked_in' });
	});

	it('404s when acting on a booking that does not exist', async () => {
		const response = await fetch(
			'http://localhost/bookings/00000000-0000-7000-8000-000000000000/cancel',
			{
				method: 'POST',
			},
		);

		expect(response.status).toBe(404);
		const body = await response.json();
		expect(body.code).toBe('NOT_FOUND');
	});
});
