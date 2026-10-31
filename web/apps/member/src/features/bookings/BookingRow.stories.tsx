import type { Booking } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { BookingRow } from './BookingRow';

// Mirrors the scenario store's seeded `confirmed` booking
// (api-client/src/scenarios/bookingsOperations.ts) so Cancel in this story
// actually succeeds against the mocked backend. Its fixed December 2026
// `start` is in the past relative to whenever this story runs, so "Check in"
// never opens here — that's a real, time-dependent gate in `isCheckInOpen`,
// not a story bug.
const BOOKING: Booking = {
	id: '0193f4c6-5a91-7c9e-cd80-7f5b2c1d0e9f',
	resourceId: '0193f4c4-3e7f-7a7c-ab6e-5d3f0a9b8c7d',
	resourceTypeId: '0193f4c4-2d6e-7f6b-ba5d-4c2e9f8a7b6c',
	siteId: '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b',
	memberId: '0193f4c5-4f80-7b8d-bc7f-6e4a1b0c9d8e',
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
	title: 'apps/member/BookingRow',
	component: BookingRow,
	tags: ['autodocs'],
	args: {
		booking: BOOKING,
		resourceLabel: 'Meeting Room A',
		expanded: false,
		onToggle: () => {},
		onChanged: () => {},
	},
} satisfies Meta<typeof BookingRow>;

export default meta;
type Story = StoryObj<typeof meta>;

// Click "Cancel" — it opens the real `ConfirmationModal` and, on confirm,
// runs against the MSW scenario handlers (see .storybook/preview.tsx).
export const Cancellable: Story = {};

export const Completed: Story = {
	args: { booking: { ...BOOKING, status: 'completed' } },
};
