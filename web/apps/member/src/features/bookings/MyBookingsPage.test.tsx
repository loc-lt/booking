import type { Booking, Resource } from '@booking-core/api-client';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { renderWithQueryClient } from '../../test-utils';
import { MyBookingsPage } from './MyBookingsPage';

const BOOKING: Booking = {
	id: 'booking-1',
	resourceId: 'resource-1',
	resourceTypeId: 'type-1',
	siteId: 'site-1',
	memberId: 'member-1',
	start: '2026-12-15T09:00:00+07:00',
	end: '2026-12-15T09:30:00+07:00',
	status: 'confirmed',
	customFieldValues: {},
	appliedConfig: {
		flowConfigVersion: 1,
		ruleSetVersion: 1,
		confirmation: 'instant',
		checkIn: { required: true, opensMinutesBefore: 15, noShowAfterMinutes: 15 },
		cancellation: { allowedUntilMinutesBefore: 60 },
	},
	history: [
		{ toStatus: 'confirmed', occurredAt: '2026-12-15T08:00:00Z', actor: { type: 'system' } },
	],
	createdAt: '2026-12-15T08:00:00+07:00',
	updatedAt: '2026-12-15T08:00:00+07:00',
};

const RESOURCE: Resource = {
	id: 'resource-1',
	resourceTypeId: 'type-1',
	siteId: 'site-1',
	label: 'Meeting Room A',
	customFieldValues: {},
	createdAt: '2026-01-01T00:00:00Z',
	updatedAt: '2026-01-01T00:00:00Z',
};

const server = setupServer(
	http.get('*/bookings', () => HttpResponse.json({ data: [BOOKING], nextCursor: null })),
	http.get('*/resources', () => HttpResponse.json({ data: [RESOURCE], nextCursor: null })),
);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('MyBookingsPage', () => {
	it('shows a loading state before bookings arrive', () => {
		renderWithQueryClient(<MyBookingsPage />);

		expect(document.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
	});

	it("resolves each booking's resource label from the matching resource", async () => {
		renderWithQueryClient(<MyBookingsPage />);

		expect(await screen.findByText('Meeting Room A')).toBeTruthy();
	});

	it('shows an empty state when there are no bookings', async () => {
		server.use(http.get('*/bookings', () => HttpResponse.json({ data: [], nextCursor: null })));
		renderWithQueryClient(<MyBookingsPage />);

		expect(await screen.findByText('No bookings yet.')).toBeTruthy();
	});

	it('shows the error code when bookings fail to load', async () => {
		server.use(
			http.get('*/bookings', () =>
				HttpResponse.json(
					{ type: 'about:blank', title: 'Forbidden', status: 403, code: 'FORBIDDEN' },
					{ status: 403 },
				),
			),
		);
		renderWithQueryClient(<MyBookingsPage />);

		expect(await screen.findByText("Couldn't load your bookings (FORBIDDEN).")).toBeTruthy();
	});

	it('expands a booking’s timeline on click, and collapses it again on a second click', async () => {
		const user = userEvent.setup();
		renderWithQueryClient(<MyBookingsPage />);

		await screen.findByText('Meeting Room A');
		expect(screen.queryByText(/System/)).toBeNull();

		await user.click(screen.getByText('Meeting Room A'));
		expect(await screen.findByText(/System/)).toBeTruthy();

		await user.click(screen.getByText('Meeting Room A'));
		expect(screen.queryByText(/System/)).toBeNull();
	});
});
