import type { BookingHistoryEntry } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { BookingTimeline } from './booking-timeline';

const MEMBER_ID = '0193f4c5-4f80-7b8d-bc7f-6e4a1b0c9d8e';

const HISTORY: BookingHistoryEntry[] = [
	{
		toStatus: 'pending_approval',
		occurredAt: '2026-12-15T08:00:00+07:00',
		actor: { type: 'user', id: MEMBER_ID },
	},
	{
		fromStatus: 'pending_approval',
		toStatus: 'confirmed',
		occurredAt: '2026-12-15T09:12:00+07:00',
		actor: { type: 'user' },
	},
	{
		fromStatus: 'confirmed',
		toStatus: 'checked_in',
		occurredAt: '2026-12-15T13:58:00+07:00',
		actor: { type: 'user', id: MEMBER_ID },
	},
];

const meta = {
	title: 'booking-ui/BookingTimeline',
	component: BookingTimeline,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		history: HISTORY,
	},
} satisfies Meta<typeof BookingTimeline>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Empty: Story = {
	args: { history: [] },
};

export const WithReasons: Story = {
	args: {
		history: [
			...HISTORY,
			{
				fromStatus: 'checked_in',
				toStatus: 'cancelled',
				occurredAt: '2026-12-15T15:00:00+07:00',
				actor: { type: 'system' },
			},
		],
		getReason: (entry) =>
			entry.toStatus === 'cancelled' ? 'Cancelled by an admin: resource needed maintenance.' : null,
	},
};
