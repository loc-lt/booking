import type { AvailabilitySlot } from '@booking-core/api-client';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AvailabilityGrid } from './AvailabilityGrid';

const FREE_SLOT: AvailabilitySlot = {
	start: '2026-12-15T09:00:00+07:00',
	end: '2026-12-15T09:30:00+07:00',
	resourceIds: ['resource-1'],
};

const TAKEN_SLOT: AvailabilitySlot = {
	start: '2026-12-15T09:30:00+07:00',
	end: '2026-12-15T10:00:00+07:00',
	resourceIds: [],
};

describe('AvailabilityGrid', () => {
	it('shows the empty state when there are no slots', () => {
		render(<AvailabilityGrid slots={[]} />);

		expect(screen.getByText('No slots available.')).toBeTruthy();
	});

	it('disables a slot with no resources still free, by default', () => {
		render(<AvailabilityGrid slots={[FREE_SLOT, TAKEN_SLOT]} />);

		const buttons = screen.getAllByRole('button') as HTMLButtonElement[];
		expect(buttons.find((b) => b.disabled)?.textContent).toContain('9:30');
		expect(buttons.find((b) => !b.disabled)?.textContent).toContain('9:00');
	});

	it('calls onSelectSlot with the clicked slot, and not for a disabled one', async () => {
		const user = userEvent.setup();
		const onSelectSlot = vi.fn();
		render(<AvailabilityGrid slots={[FREE_SLOT, TAKEN_SLOT]} onSelectSlot={onSelectSlot} />);

		await user.click(screen.getByText(/9:00/));
		expect(onSelectSlot).toHaveBeenCalledWith(FREE_SLOT);

		await user.click(screen.getByText(/9:30/));
		expect(onSelectSlot).toHaveBeenCalledTimes(1);
	});

	it('lets a consumer override how a slot is disabled', () => {
		render(<AvailabilityGrid slots={[FREE_SLOT]} isSlotDisabled={() => true} />);

		expect((screen.getByRole('button') as HTMLButtonElement).disabled).toBe(true);
	});

	it('hands full control to a renderSlot slot', () => {
		render(
			<AvailabilityGrid
				slots={[FREE_SLOT]}
				renderSlot={(slot, state) => (
					<span>
						custom {slot.start} {state.disabled ? 'disabled' : 'free'}
					</span>
				)}
			/>,
		);

		expect(screen.getByText(/custom .* free/)).toBeTruthy();
		expect(screen.queryByRole('button')).toBeNull();
	});
});
