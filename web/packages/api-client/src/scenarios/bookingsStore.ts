import { delay, HttpResponse, http } from 'msw';
import type {
	Actor,
	AppliedConfig,
	Booking,
	BookingHistoryEntry,
	CreateBookingRequest,
	RejectBookingRequest,
	RuleReason,
} from '../generated/models';

/**
 * Stateful mock backend for availability and bookings, kept in memory for the
 * life of the tab. Exercises the cases the generated random/canned handlers
 * can't: a slot taken by an existing booking, a rule denying a request with
 * reasons, and the lifecycle actions actually moving a booking's status.
 */

const DEMO_SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';
const MEETING_ROOM_TYPE_ID = '0193f4c4-2d6e-7f6b-ba5d-4c2e9f8a7b6c';
const MEETING_ROOM_A_ID = '0193f4c4-3e7f-7a7c-ab6e-5d3f0a9b8c7d';
const MEMBER_ID = '0193f4c5-4f80-7b8d-bc7f-6e4a1b0c9d8e';

/** Booking a slot starting at this hour is denied by the demo "no early bookings" rule. */
const DENIED_START_HOUR = 7;

const SEEDED_APPLIED_CONFIG: AppliedConfig = {
	flowConfigVersion: 1,
	ruleSetVersion: 1,
	confirmation: 'instant',
	checkIn: { required: true, opensMinutesBefore: 15, noShowAfterMinutes: 15 },
	cancellation: { allowedUntilMinutesBefore: 60 },
};

function seedBookings(): Booking[] {
	const createdAt = '2026-12-15T08:00:00+07:00';
	return [
		{
			id: '0193f4c6-5a91-7c9e-cd80-7f5b2c1d0e9f',
			resourceId: MEETING_ROOM_A_ID,
			resourceTypeId: MEETING_ROOM_TYPE_ID,
			siteId: DEMO_SITE_ID,
			memberId: MEMBER_ID,
			start: '2026-12-15T09:00:00+07:00',
			end: '2026-12-15T09:30:00+07:00',
			status: 'confirmed',
			customFieldValues: {},
			appliedConfig: SEEDED_APPLIED_CONFIG,
			history: [
				{
					toStatus: 'confirmed',
					occurredAt: createdAt,
					actor: { type: 'user', id: MEMBER_ID },
				},
			],
			createdAt,
			updatedAt: createdAt,
		},
	];
}

let bookings = seedBookings();

/** Restores the seeded bookings. Call between tests. */
export function resetBookingsScenario(): void {
	bookings = seedBookings();
}

function notFound(detail: string) {
	return HttpResponse.json(
		{ type: 'about:blank', title: 'Not found', status: 404, code: 'NOT_FOUND', detail },
		{ status: 404 },
	);
}

function slotTaken() {
	return HttpResponse.json(
		{
			type: 'about:blank',
			title: 'Slot taken',
			status: 409,
			code: 'SLOT_TAKEN',
			detail: 'Someone else holds this slot.',
		},
		{ status: 409 },
	);
}

function invalidTransition(detail: string) {
	return HttpResponse.json(
		{
			type: 'about:blank',
			title: 'Invalid transition',
			status: 409,
			code: 'INVALID_TRANSITION',
			detail,
		},
		{ status: 409 },
	);
}

function bookingDenied(reasons: RuleReason[]) {
	return HttpResponse.json(
		{
			type: 'https://errors.bookingcore.dev/booking-denied',
			title: 'Booking not allowed',
			status: 422,
			code: 'BOOKING_DENIED',
			reasons,
		},
		{ status: 422 },
	);
}

function overlaps(aStart: string, aEnd: string, bStart: string, bEnd: string): boolean {
	return aStart < bEnd && bStart < aEnd;
}

const ACTIVE_STATUSES = new Set([
	'awaiting_payment',
	'pending_approval',
	'confirmed',
	'checked_in',
]);

function isResourceFree(resourceId: string, start: string, end: string): boolean {
	return !bookings.some(
		(booking) =>
			booking.resourceId === resourceId &&
			ACTIVE_STATUSES.has(booking.status) &&
			overlaps(booking.start, booking.end, start, end),
	);
}

function transition(booking: Booking, toStatus: Booking['status'], actor: Actor): Booking {
	const occurredAt = new Date().toISOString();
	const entry: BookingHistoryEntry = { fromStatus: booking.status, toStatus, occurredAt, actor };
	const updated: Booking = {
		...booking,
		status: toStatus,
		history: [...booking.history, entry],
		updatedAt: occurredAt,
	};
	bookings = bookings.map((existing) => (existing.id === updated.id ? updated : existing));
	return updated;
}

export const bookingsScenarioHandlers = [
	http.get('*/availability', async ({ request }) => {
		await delay(300);
		const url = new URL(request.url);
		const siteId = url.searchParams.get('siteId') ?? DEMO_SITE_ID;
		const resourceTypeId = url.searchParams.get('resourceTypeId') ?? MEETING_ROOM_TYPE_ID;
		const date = url.searchParams.get('date') ?? '2026-12-15';
		const onlyResourceId = url.searchParams.get('resourceId');
		const resourceIds = onlyResourceId ? [onlyResourceId] : [MEETING_ROOM_A_ID];

		const slotMinutes = 30;
		const slots = Array.from({ length: 4 }, (_, i) => {
			const hour = 9 + Math.floor((i * slotMinutes) / 60);
			const minute = (i * slotMinutes) % 60;
			const start = `${date}T${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:00+07:00`;
			const endMinuteTotal = hour * 60 + minute + slotMinutes;
			const end = `${date}T${String(Math.floor(endMinuteTotal / 60)).padStart(2, '0')}:${String(
				endMinuteTotal % 60,
			).padStart(2, '0')}:00+07:00`;
			return {
				start,
				end,
				resourceIds: resourceIds.filter((resourceId) => isResourceFree(resourceId, start, end)),
			};
		});

		return HttpResponse.json({ siteId, resourceTypeId, date, slotMinutes, slots });
	}),

	http.get('*/bookings', async ({ request }) => {
		await delay(300);
		const url = new URL(request.url);
		const resourceId = url.searchParams.get('resourceId');
		const resourceTypeId = url.searchParams.get('resourceTypeId');
		const siteId = url.searchParams.get('siteId');
		const memberId = url.searchParams.get('memberId');
		const status = url.searchParams.get('status');

		const filtered = bookings.filter(
			(booking) =>
				(!resourceId || booking.resourceId === resourceId) &&
				(!resourceTypeId || booking.resourceTypeId === resourceTypeId) &&
				(!siteId || booking.siteId === siteId) &&
				(!memberId || booking.memberId === memberId) &&
				(!status || booking.status === status),
		);
		return HttpResponse.json({ data: filtered, nextCursor: null });
	}),

	http.post('*/bookings', async ({ request }) => {
		const body = (await request.json()) as CreateBookingRequest;
		await delay(300);

		const startHour = Number(body.start.slice(11, 13));
		if (startHour === DENIED_START_HOUR) {
			return bookingDenied([
				{ ruleId: 'no-early-bookings', message: 'This resource cannot be booked before 9am.' },
			]);
		}

		if (!isResourceFree(body.resourceId, body.start, body.end)) {
			return slotTaken();
		}

		const now = new Date().toISOString();
		const created: Booking = {
			id: crypto.randomUUID(),
			resourceId: body.resourceId,
			resourceTypeId: MEETING_ROOM_TYPE_ID,
			siteId: DEMO_SITE_ID,
			memberId: body.memberId ?? MEMBER_ID,
			start: body.start,
			end: body.end,
			status: 'confirmed',
			customFieldValues: body.customFieldValues ?? {},
			appliedConfig: SEEDED_APPLIED_CONFIG,
			history: [
				{
					toStatus: 'confirmed',
					occurredAt: now,
					actor: { type: 'user', id: body.memberId ?? MEMBER_ID },
				},
			],
			createdAt: now,
			updatedAt: now,
		};
		bookings = [created, ...bookings];
		return HttpResponse.json(created, { status: 201 });
	}),

	http.get('*/bookings/:bookingId', async ({ params }) => {
		await delay(300);
		const found = bookings.find((booking) => booking.id === params.bookingId);
		return found ? HttpResponse.json(found) : notFound('No booking with that id.');
	}),

	http.post('*/bookings/:bookingId/check-in', async ({ params }) => {
		await delay(300);
		const found = bookings.find((booking) => booking.id === params.bookingId);
		if (!found) return notFound('No booking with that id.');
		if (found.status !== 'confirmed') {
			return invalidTransition(`Cannot check in a booking in status ${found.status}.`);
		}
		return HttpResponse.json(transition(found, 'checked_in', { type: 'user', id: found.memberId }));
	}),

	http.post('*/bookings/:bookingId/cancel', async ({ params }) => {
		await delay(300);
		const found = bookings.find((booking) => booking.id === params.bookingId);
		if (!found) return notFound('No booking with that id.');
		if (!ACTIVE_STATUSES.has(found.status) || found.status === 'checked_in') {
			return invalidTransition(`Cannot cancel a booking in status ${found.status}.`);
		}
		return HttpResponse.json(transition(found, 'cancelled', { type: 'user', id: found.memberId }));
	}),

	http.post('*/bookings/:bookingId/approve', async ({ params }) => {
		await delay(300);
		const found = bookings.find((booking) => booking.id === params.bookingId);
		if (!found) return notFound('No booking with that id.');
		if (found.status !== 'pending_approval') {
			return invalidTransition(`Cannot approve a booking in status ${found.status}.`);
		}
		return HttpResponse.json(transition(found, 'confirmed', { type: 'system' }));
	}),

	http.post('*/bookings/:bookingId/reject', async ({ params, request }) => {
		await delay(300);
		const found = bookings.find((booking) => booking.id === params.bookingId);
		if (!found) return notFound('No booking with that id.');
		if (found.status !== 'pending_approval') {
			return invalidTransition(`Cannot reject a booking in status ${found.status}.`);
		}
		await (request.json() as Promise<RejectBookingRequest>);
		return HttpResponse.json(transition(found, 'rejected', { type: 'system' }));
	}),
];
