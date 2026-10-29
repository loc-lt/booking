import type { Booking } from '@booking-core/api-client';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { BookingCard } from './BookingCard';

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
	history: [],
	createdAt: '2026-12-15T08:00:00+07:00',
	updatedAt: '2026-12-15T08:00:00+07:00',
};

describe('BookingCard', () => {
	it('falls back to a generic resource label when none is given', () => {
		render(<BookingCard booking={BOOKING} />);

		expect(screen.getByText('Resource')).toBeTruthy();
	});

	it('shows the given resource label and the booking status', () => {
		render(<BookingCard booking={BOOKING} resourceLabel='Meeting Room A' />);

		expect(screen.getByText('Meeting Room A')).toBeTruthy();
		expect(screen.getByText('Confirmed')).toBeTruthy();
	});

	it('hands full control to a renderResource slot', () => {
		render(<BookingCard booking={BOOKING} renderResource={(b) => `Booking ${b.id}`} />);

		expect(screen.getByText('Booking booking-1')).toBeTruthy();
	});

	it('renders app-owned actions in the action slot', () => {
		render(<BookingCard booking={BOOKING} actions={<button type='button'>Cancel</button>} />);

		expect(screen.getByRole('button', { name: 'Cancel' })).toBeTruthy();
	});

	it('calls onClick when the card is clicked', async () => {
		const user = userEvent.setup();
		const onClick = vi.fn();
		render(<BookingCard booking={BOOKING} onClick={onClick} />);

		await user.click(screen.getByText('Resource'));
		expect(onClick).toHaveBeenCalledOnce();
	});
});
