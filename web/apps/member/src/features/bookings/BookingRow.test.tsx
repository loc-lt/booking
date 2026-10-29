import type { Booking, BookingStatus } from '@booking-core/api-client';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { renderWithQueryClient } from '../../test-utils';
import { BookingRow } from './BookingRow';

function booking(status: BookingStatus, overrides: Partial<Booking> = {}): Booking {
	return {
		id: 'booking-1',
		resourceId: 'resource-1',
		resourceTypeId: 'type-1',
		siteId: 'site-1',
		memberId: 'member-1',
		start: '2026-12-15T09:00:00+07:00',
		end: '2026-12-15T09:30:00+07:00',
		status,
		customFieldValues: {},
		appliedConfig: {
			flowConfigVersion: 1,
			ruleSetVersion: 1,
			confirmation: 'instant',
			checkIn: { required: true, opensMinutesBefore: 15, noShowAfterMinutes: 15 },
			cancellation: { allowedUntilMinutesBefore: 60 },
		},
		history: [],
		createdAt: '2026-12-15T08:00:00+07:00',
		updatedAt: '2026-12-15T08:00:00+07:00',
		...overrides,
	};
}

const server = setupServer(
	http.post('*/bookings/:id/check-in', () => HttpResponse.json(booking('checked_in'))),
	http.post('*/bookings/:id/cancel', () => HttpResponse.json(booking('cancelled'))),
);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('BookingRow', () => {
	it('shows Check in and Cancel for a confirmed booking', () => {
		renderWithQueryClient(
			<BookingRow
				booking={booking('confirmed')}
				resourceLabel='Meeting Room A'
				expanded={false}
				onToggle={vi.fn()}
				onChanged={vi.fn()}
			/>,
		);

		expect(screen.getByRole('button', { name: 'Check in' })).toBeTruthy();
		expect(screen.getByRole('button', { name: 'Cancel' })).toBeTruthy();
	});

	it('hides both actions once the booking is checked in, since neither move is allowed from there', () => {
		renderWithQueryClient(
			<BookingRow
				booking={booking('checked_in')}
				resourceLabel='Meeting Room A'
				expanded={false}
				onToggle={vi.fn()}
				onChanged={vi.fn()}
			/>,
		);

		expect(screen.queryByRole('button', { name: 'Check in' })).toBeNull();
		expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull();
	});

	it('calls onChanged after a successful check-in, without toggling the row open', async () => {
		const user = userEvent.setup();
		const onToggle = vi.fn();
		const onChanged = vi.fn();
		renderWithQueryClient(
			<BookingRow
				booking={booking('confirmed')}
				resourceLabel='Meeting Room A'
				expanded={false}
				onToggle={onToggle}
				onChanged={onChanged}
			/>,
		);

		await user.click(screen.getByRole('button', { name: 'Check in' }));

		await vi.waitFor(() => expect(onChanged).toHaveBeenCalledOnce());
		expect(onToggle).not.toHaveBeenCalled();
	});

	it('shows the error code when cancelling fails', async () => {
		server.use(
			http.post('*/bookings/:id/cancel', () =>
				HttpResponse.json(
					{ type: 'about:blank', title: 'Conflict', status: 409, code: 'INVALID_TRANSITION' },
					{ status: 409 },
				),
			),
		);
		const user = userEvent.setup();
		renderWithQueryClient(
			<BookingRow
				booking={booking('confirmed')}
				resourceLabel='Meeting Room A'
				expanded={false}
				onToggle={vi.fn()}
				onChanged={vi.fn()}
			/>,
		);

		await user.click(screen.getByRole('button', { name: 'Cancel' }));

		expect(
			await screen.findByText("Couldn't update the booking (INVALID_TRANSITION)."),
		).toBeTruthy();
	});

	it('shows the timeline only when expanded', () => {
		const withHistory = booking('confirmed', {
			history: [
				{ toStatus: 'confirmed', occurredAt: '2026-12-15T08:00:00Z', actor: { type: 'system' } },
			],
		});

		renderWithQueryClient(
			<BookingRow
				booking={withHistory}
				resourceLabel='Meeting Room A'
				expanded={false}
				onToggle={vi.fn()}
				onChanged={vi.fn()}
			/>,
		);
		expect(screen.queryByText(/System/)).toBeNull();
	});

	it('shows history entries when expanded', () => {
		const withHistory = booking('confirmed', {
			history: [
				{ toStatus: 'confirmed', occurredAt: '2026-12-15T08:00:00Z', actor: { type: 'system' } },
			],
		});

		renderWithQueryClient(
			<BookingRow
				booking={withHistory}
				resourceLabel='Meeting Room A'
				expanded
				onToggle={vi.fn()}
				onChanged={vi.fn()}
			/>,
		);
		expect(screen.getByText(/System/)).toBeTruthy();
	});
});
