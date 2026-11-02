import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { bookingsScenarioHandlers, resetBookingsScenario } from './bookingsStore';
import { resetResourceTypesScenario, resourceTypesScenarioHandlers } from './resourceTypesStore';

const MEETING_ROOM_A_ID = '0193f4c4-3e7f-7a7c-ab6e-5d3f0a9b8c7d';
const SEEDED_BOOKING_ID = '0193f4c6-5a91-7c9e-cd80-7f5b2c1d0e9f';

const server = setupServer(...bookingsScenarioHandlers, ...resourceTypesScenarioHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
beforeEach(() => {
	resetBookingsScenario();
	resetResourceTypesScenario();
});

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

	it('creates a pending_approval booking for a resource whose type requires approval', async () => {
		const typeResponse = await fetch('http://localhost/resource-types', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				key: 'approval_room',
				label: 'Approval room',
				fields: [],
				flowConfig: {
					confirmation: 'approval',
					checkIn: { required: true, opensMinutesBefore: 15, noShowAfterMinutes: 15 },
					cancellation: { allowedUntilMinutesBefore: 60 },
				},
			}),
		});
		const resourceType = await typeResponse.json();

		const resourceResponse = await fetch('http://localhost/resources', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				resourceTypeId: resourceType.id,
				siteId: '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b',
				label: 'Approval Room 1',
			}),
		});
		const resource = await resourceResponse.json();

		const bookingResponse = await fetch('http://localhost/bookings', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				resourceId: resource.id,
				start: '2026-12-15T10:00:00+07:00',
				end: '2026-12-15T10:30:00+07:00',
			}),
		});

		expect(bookingResponse.status).toBe(201);
		const body = await bookingResponse.json();
		expect(body.status).toBe('pending_approval');
		expect(body.appliedConfig.confirmation).toBe('approval');
		expect(body.history).toEqual([expect.objectContaining({ toStatus: 'pending_approval' })]);
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
