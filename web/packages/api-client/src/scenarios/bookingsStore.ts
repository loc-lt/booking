import { delay, HttpResponse, http } from 'msw';
import type { CreateBookingRequest, RejectBookingRequest } from '../generated/models';
import {
	approveOp,
	cancelOp,
	checkInOp,
	createBookingOp,
	getBookingOp,
	listBookingsOp,
	rejectOp,
	resetBookingsState,
	searchAvailabilityOp,
} from './bookingsOperations';

/**
 * In-browser MSW adapter over bookingsOperations.ts, for solo dev (one tab,
 * mocks reset on reload) and tests. For a shared backend across apps, see
 * mock-server/, which calls the same operations over real HTTP.
 */

/** Restores the seeded bookings. Call between tests. */
export function resetBookingsScenario(): void {
	resetBookingsState();
}

function json(result: { status: number; body: unknown }) {
	return HttpResponse.json(result.body as Parameters<typeof HttpResponse.json>[0], {
		status: result.status,
	});
}

export const bookingsScenarioHandlers = [
	http.get('*/availability', async ({ request }) => {
		await delay(300);
		const url = new URL(request.url);
		return json(
			searchAvailabilityOp({
				siteId: url.searchParams.get('siteId'),
				resourceTypeId: url.searchParams.get('resourceTypeId'),
				resourceId: url.searchParams.get('resourceId'),
				date: url.searchParams.get('date'),
			}),
		);
	}),

	http.get('*/bookings', async ({ request }) => {
		await delay(300);
		const url = new URL(request.url);
		return json(
			listBookingsOp({
				resourceId: url.searchParams.get('resourceId'),
				resourceTypeId: url.searchParams.get('resourceTypeId'),
				siteId: url.searchParams.get('siteId'),
				memberId: url.searchParams.get('memberId'),
				status: url.searchParams.get('status'),
			}),
		);
	}),

	http.post('*/bookings', async ({ request }) => {
		const requestBody = (await request.json()) as CreateBookingRequest;
		await delay(300);
		return json(createBookingOp(requestBody));
	}),

	http.get('*/bookings/:bookingId', async ({ params }) => {
		await delay(300);
		return json(getBookingOp(params.bookingId as string));
	}),

	http.post('*/bookings/:bookingId/check-in', async ({ params }) => {
		await delay(300);
		return json(checkInOp(params.bookingId as string));
	}),

	http.post('*/bookings/:bookingId/cancel', async ({ params }) => {
		await delay(300);
		return json(cancelOp(params.bookingId as string));
	}),

	http.post('*/bookings/:bookingId/approve', async ({ params }) => {
		await delay(300);
		return json(approveOp(params.bookingId as string));
	}),

	http.post('*/bookings/:bookingId/reject', async ({ params, request }) => {
		const requestBody = (await request.json()) as RejectBookingRequest;
		await delay(300);
		return json(rejectOp(params.bookingId as string, requestBody));
	}),
];
