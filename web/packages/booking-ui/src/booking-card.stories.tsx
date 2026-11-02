import type { Booking } from '@booking-core/api-client';
import { Button } from '@booking-core/ui';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { BookingCard } from './booking-card';

const BOOKING: Booking = {
	id: '0193f4c7-6ba2-7dae-de91-805c3d2e1f0a',
	resourceId: '0193f4c4-3e7f-7a7c-ab6e-5d3f0a9b8c7d',
	resourceTypeId: '0193f4c4-2d6e-7f6b-ba5d-4c2e9f8a7b6c',
	siteId: '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b',
	memberId: '0193f4c5-4f80-7b8d-bc7f-6e4a1b0c9d8e',
	start: '2026-12-15T14:00:00+07:00',
	end: '2026-12-15T16:30:00+07:00',
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
		{
			toStatus: 'confirmed',
			occurredAt: '2026-12-15T08:00:00+07:00',
			actor: { type: 'user', id: '0193f4c5-4f80-7b8d-bc7f-6e4a1b0c9d8e' },
		},
	],
	createdAt: '2026-12-15T08:00:00+07:00',
	updatedAt: '2026-12-15T08:00:00+07:00',
};

const meta = {
	title: 'booking-ui/BookingCard',
	component: BookingCard,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		booking: BOOKING,
		resourceLabel: 'Meeting Room A',
	},
} satisfies Meta<typeof BookingCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithActions: Story = {
	args: {
		actions: (
			<Button size='sm' variant='ghost'>
				Cancel
			</Button>
		),
	},
};

export const Clickable: Story = {
	args: { onClick: () => {} },
};

export const PendingApproval: Story = {
	args: { booking: { ...BOOKING, status: 'pending_approval' } },
};
