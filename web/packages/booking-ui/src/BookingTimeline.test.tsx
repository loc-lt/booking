import type { BookingHistoryEntry } from '@booking-core/api-client';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BookingTimeline } from './BookingTimeline';

const SUBMITTED: BookingHistoryEntry = {
	toStatus: 'confirmed',
	occurredAt: '2026-12-15T08:00:00Z',
	actor: { type: 'user', id: 'member-1' },
};

const CANCELLED: BookingHistoryEntry = {
	fromStatus: 'confirmed',
	toStatus: 'cancelled',
	occurredAt: '2026-12-15T09:00:00Z',
	actor: { type: 'system' },
};

describe('BookingTimeline', () => {
	it('shows the empty state when there is no history', () => {
		render(<BookingTimeline history={[]} />);

		expect(screen.getByText('No history yet.')).toBeTruthy();
	});

	it('shows only a "to" status for the first entry, and "from → to" for later ones', () => {
		render(<BookingTimeline history={[SUBMITTED, CANCELLED]} />);

		expect(screen.getAllByText('Confirmed').length).toBe(2); // SUBMITTED's "to" and CANCELLED's "from"
		expect(screen.getByText('Cancelled')).toBeTruthy();
	});

	it('defaults actor rendering to "Member" / "System" by actor type', () => {
		render(<BookingTimeline history={[SUBMITTED, CANCELLED]} />);

		expect(screen.getByText(/Member/)).toBeTruthy();
		expect(screen.getByText(/System/)).toBeTruthy();
	});

	it('lets a consumer resolve an actor to a real name', () => {
		render(<BookingTimeline history={[SUBMITTED]} renderActor={(actor) => `User ${actor.id}`} />);

		expect(screen.getByText(/User member-1/)).toBeTruthy();
	});

	it('shows a reason supplied via the getReason slot', () => {
		render(
			<BookingTimeline
				history={[CANCELLED]}
				getReason={(entry) => (entry.toStatus === 'cancelled' ? 'No longer needed' : undefined)}
			/>,
		);

		expect(screen.getByText('No longer needed')).toBeTruthy();
	});
});
