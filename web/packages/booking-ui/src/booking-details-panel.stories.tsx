import type { Booking, BookingStatus, FieldDefinition } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { BookingDetailsPanel } from './booking-details-panel';

const RESOURCE_ID = '0193f4c4-3e7f-7a7c-ab6e-5d3f0a9b8c7d';
const RESOURCE_TYPE_ID = '0193f4c4-2d6e-7f6b-ba5d-4c2e9f8a7b6c';
const SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';
const MEMBER_ID = '0193f4c5-4f80-7b8d-bc7f-6e4a1b0c9d8e';

function makeBooking(status: BookingStatus): Booking {
	return {
		id: '0193f4c7-6ba2-7dae-de91-805c3d2e1f0a',
		resourceId: RESOURCE_ID,
		resourceTypeId: RESOURCE_TYPE_ID,
		siteId: SITE_ID,
		memberId: MEMBER_ID,
		start: '2026-12-15T14:00:00+07:00',
		end: '2026-12-15T15:00:00+07:00',
		status,
		customFieldValues: { attendees: 4 },
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
				occurredAt: '2026-12-10T08:00:00+07:00',
				actor: { type: 'user', id: MEMBER_ID },
			},
		],
		createdAt: '2026-12-10T08:00:00+07:00',
		updatedAt: '2026-12-10T08:00:00+07:00',
	};
}

const FIELDS: FieldDefinition[] = [{ key: 'attendees', label: 'Attendees', type: 'number' }];

const meta = {
	title: 'booking-ui/BookingDetailsPanel',
	component: BookingDetailsPanel,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		booking: makeBooking('confirmed'),
		resourceLabel: 'Meeting Room A',
		fields: FIELDS,
		onApprove: () => {},
		onCancel: () => {},
		onCheckIn: () => {},
		onReject: () => {},
	},
} satisfies Meta<typeof BookingDetailsPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const PendingApproval: Story = {
	args: { booking: makeBooking('pending_approval') },
};

/** `now` falls inside the check-in window (opens 15 min before start) — both Check in and Cancel show. */
export const ConfirmedCheckInOpen: Story = {
	args: { now: new Date('2026-12-15T13:50:00+07:00') },
};

/** `now` is well before the check-in window opens — only Cancel shows. */
export const ConfirmedCheckInNotYetOpen: Story = {
	args: { now: new Date('2026-12-15T09:00:00+07:00') },
};

/** Checked in — neither check-in nor cancel apply any more. */
export const CheckedIn: Story = {
	args: { booking: makeBooking('checked_in') },
};

/** A past, released booking — read-only, no actions regardless of which handlers are passed. */
export const Cancelled: Story = {
	args: { booking: makeBooking('cancelled') },
};

export const Loading: Story = {
	args: { isCancelling: true },
};

export const WithError: Story = {
	args: {
		error: (
			<p className='text-destructive text-sm'>Couldn't update the booking (INVALID_TRANSITION).</p>
		),
	},
};

/** Omitting a handler hides that action entirely, regardless of what the status would otherwise allow — e.g. a member's calendar never offers Approve/Reject/Check-in. */
export const CancelOnly: Story = {
	args: { onApprove: undefined, onCheckIn: undefined, onReject: undefined },
};
