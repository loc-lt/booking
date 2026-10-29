import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BookingStatusBadge } from './BookingStatusBadge';

describe('BookingStatusBadge', () => {
	it('shows the generic default label for a status', () => {
		render(<BookingStatusBadge status='checked_in' />);

		expect(screen.getByText('Checked in')).toBeTruthy();
	});

	it('shows an overridden label when the tenant has renamed the status', () => {
		render(<BookingStatusBadge status='confirmed' labels={{ confirmed: 'Reserved' }} />);

		expect(screen.getByText('Reserved')).toBeTruthy();
		expect(screen.queryByText('Confirmed')).toBeNull();
	});

	it('leaves other statuses at their default label when only one is overridden', () => {
		render(<BookingStatusBadge status='cancelled' labels={{ confirmed: 'Reserved' }} />);

		expect(screen.getByText('Cancelled')).toBeTruthy();
	});
});
