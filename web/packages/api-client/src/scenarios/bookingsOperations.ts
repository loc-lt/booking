import type {
	Actor,
	AppliedConfig,
	Booking,
	BookingHistoryEntry,
	CreateBookingRequest,
	RejectBookingRequest,
	RuleReason,
} from '../generated/models';
import { findResource, findResourceType, type OperationResult } from './resourceTypesOperations';

/**
 * Transport-agnostic availability/booking operations: the same demo "backend"
 * logic used by the in-browser MSW scenario (bookingsStore.ts, for solo dev
 * and tests) and by the shared mock server (mock-server/, so console and
 * member see each other's data). Kept framework-free so both can call it.
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

const SEEDED_APPROVAL_CONFIG: AppliedConfig = {
	...SEEDED_APPLIED_CONFIG,
	confirmation: 'approval',
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
		{
			id: '0193f4c7-6ba2-7dae-de91-805c3d2e1f0a',
			resourceId: MEETING_ROOM_A_ID,
			resourceTypeId: MEETING_ROOM_TYPE_ID,
			siteId: DEMO_SITE_ID,
			memberId: MEMBER_ID,
			start: '2026-12-15T14:00:00+07:00',
			end: '2026-12-15T16:30:00+07:00',
			status: 'pending_approval',
			customFieldValues: {},
			appliedConfig: SEEDED_APPROVAL_CONFIG,
			history: [
				{
					toStatus: 'pending_approval',
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
export function resetBookingsState(): void {
	bookings = seedBookings();
}

function notFound(detail: string): OperationResult<unknown> {
	return {
		status: 404,
		body: { type: 'about:blank', title: 'Not found', status: 404, code: 'NOT_FOUND', detail },
	};
}

function slotTaken(): OperationResult<unknown> {
	return {
		status: 409,
		body: {
			type: 'about:blank',
			title: 'Slot taken',
			status: 409,
			code: 'SLOT_TAKEN',
			detail: 'Someone else holds this slot.',
		},
	};
}

function invalidTransition(detail: string): OperationResult<unknown> {
	return {
		status: 409,
		body: {
			type: 'about:blank',
			title: 'Invalid transition',
			status: 409,
			code: 'INVALID_TRANSITION',
			detail,
		},
	};
}

function bookingDenied(reasons: RuleReason[]): OperationResult<unknown> {
	return {
		status: 422,
		body: {
			type: 'https://errors.bookingcore.dev/booking-denied',
			title: 'Booking not allowed',
			status: 422,
			code: 'BOOKING_DENIED',
			reasons,
		},
	};
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

export function searchAvailabilityOp(query: {
	siteId?: string | null;
	resourceTypeId?: string | null;
	resourceId?: string | null;
	date?: string | null;
}): OperationResult<unknown> {
	const siteId = query.siteId ?? DEMO_SITE_ID;
	const resourceTypeId = query.resourceTypeId ?? MEETING_ROOM_TYPE_ID;
	const date = query.date ?? '2026-12-15';
	const resourceIds = query.resourceId ? [query.resourceId] : [MEETING_ROOM_A_ID];

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

	return { status: 200, body: { siteId, resourceTypeId, date, slotMinutes, slots } };
}

export function listBookingsOp(query: {
	resourceId?: string | null;
	resourceTypeId?: string | null;
	siteId?: string | null;
	memberId?: string | null;
	status?: string | null;
}): OperationResult<{ data: Booking[]; nextCursor: null }> {
	const filtered = bookings.filter(
		(booking) =>
			(!query.resourceId || booking.resourceId === query.resourceId) &&
			(!query.resourceTypeId || booking.resourceTypeId === query.resourceTypeId) &&
			(!query.siteId || booking.siteId === query.siteId) &&
			(!query.memberId || booking.memberId === query.memberId) &&
			(!query.status || booking.status === query.status),
	);
	return { status: 200, body: { data: filtered, nextCursor: null } };
}

export function createBookingOp(body: CreateBookingRequest): OperationResult<unknown> {
	const startHour = Number(body.start.slice(11, 13));
	if (startHour === DENIED_START_HOUR) {
		return bookingDenied([
			{ ruleId: 'no-early-bookings', message: 'This resource cannot be booked before 9am.' },
		]);
	}

	if (!isResourceFree(body.resourceId, body.start, body.end)) {
		return slotTaken();
	}

	// The demo's always-seeded meeting room isn't itself in resourceTypesOperations'
	// seed data, so fall back to its fixed type/site when the resource isn't found
	// there (e.g. a type created via the console that hasn't added this resource).
	const resource = findResource(body.resourceId);
	const resourceTypeId = resource?.resourceTypeId ?? MEETING_ROOM_TYPE_ID;
	const resourceType = findResourceType(resourceTypeId);
	const appliedConfig: AppliedConfig = resourceType
		? {
				flowConfigVersion: resourceType.version,
				ruleSetVersion: 1,
				...resourceType.flowConfig,
			}
		: SEEDED_APPLIED_CONFIG;
	const status = appliedConfig.confirmation === 'approval' ? 'pending_approval' : 'confirmed';
	const now = new Date().toISOString();
	const created: Booking = {
		id: crypto.randomUUID(),
		resourceId: body.resourceId,
		resourceTypeId,
		siteId: resource?.siteId ?? DEMO_SITE_ID,
		memberId: body.memberId ?? MEMBER_ID,
		start: body.start,
		end: body.end,
		status,
		customFieldValues: body.customFieldValues ?? {},
		appliedConfig,
		history: [
			{
				toStatus: status,
				occurredAt: now,
				actor: { type: 'user', id: body.memberId ?? MEMBER_ID },
			},
		],
		createdAt: now,
		updatedAt: now,
	};
	bookings = [created, ...bookings];
	return { status: 201, body: created };
}

export function getBookingOp(bookingId: string): OperationResult<unknown> {
	const found = bookings.find((booking) => booking.id === bookingId);
	return found ? { status: 200, body: found } : notFound('No booking with that id.');
}

export function checkInOp(bookingId: string): OperationResult<unknown> {
	const found = bookings.find((booking) => booking.id === bookingId);
	if (!found) return notFound('No booking with that id.');
	if (found.status !== 'confirmed') {
		return invalidTransition(`Cannot check in a booking in status ${found.status}.`);
	}
	return {
		status: 200,
		body: transition(found, 'checked_in', { type: 'user', id: found.memberId }),
	};
}

export function cancelOp(bookingId: string): OperationResult<unknown> {
	const found = bookings.find((booking) => booking.id === bookingId);
	if (!found) return notFound('No booking with that id.');
	if (!ACTIVE_STATUSES.has(found.status) || found.status === 'checked_in') {
		return invalidTransition(`Cannot cancel a booking in status ${found.status}.`);
	}
	return {
		status: 200,
		body: transition(found, 'cancelled', { type: 'user', id: found.memberId }),
	};
}

export function approveOp(bookingId: string): OperationResult<unknown> {
	const found = bookings.find((booking) => booking.id === bookingId);
	if (!found) return notFound('No booking with that id.');
	if (found.status !== 'pending_approval') {
		return invalidTransition(`Cannot approve a booking in status ${found.status}.`);
	}
	return { status: 200, body: transition(found, 'confirmed', { type: 'system' }) };
}

export function rejectOp(bookingId: string, _body: RejectBookingRequest): OperationResult<unknown> {
	const found = bookings.find((booking) => booking.id === bookingId);
	if (!found) return notFound('No booking with that id.');
	if (found.status !== 'pending_approval') {
		return invalidTransition(`Cannot reject a booking in status ${found.status}.`);
	}
	return { status: 200, body: transition(found, 'rejected', { type: 'system' }) };
}
