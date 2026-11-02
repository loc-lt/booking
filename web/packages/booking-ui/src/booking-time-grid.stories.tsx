import type { Booking, BookingStatus } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import type { TimeRange } from './booking-occupancy';
import { BookingTimeGrid } from './booking-time-grid';

const RESOURCE_ID = '0193f4c4-3e7f-7a7c-ab6e-5d3f0a9b8c7d';
const RESOURCE_TYPE_ID = '0193f4c4-2d6e-7f6b-ba5d-4c2e9f8a7b6c';
const SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';
const MEMBER_ID = '0193f4c5-4f80-7b8d-bc7f-6e4a1b0c9d8e';

const DAYS = [
	'2026-12-14',
	'2026-12-15',
	'2026-12-16',
	'2026-12-17',
	'2026-12-18',
	'2026-12-19',
	'2026-12-20',
];

function makeBooking(id: string, start: string, end: string, status: BookingStatus): Booking {
	return {
		id,
		resourceId: RESOURCE_ID,
		resourceTypeId: RESOURCE_TYPE_ID,
		siteId: SITE_ID,
		memberId: MEMBER_ID,
		start,
		end,
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
		createdAt: start,
		updatedAt: start,
	};
}

function makeBookingsByDay(): Map<string, Booking[]> {
	const byDay = new Map<string, Booking[]>();
	byDay.set('2026-12-15', [
		makeBooking('a', '2026-12-15T09:00:00+07:00', '2026-12-15T09:30:00+07:00', 'confirmed'),
		makeBooking('b', '2026-12-15T14:00:00+07:00', '2026-12-15T16:30:00+07:00', 'pending_approval'),
	]);
	byDay.set('2026-12-17', [
		makeBooking('c', '2026-12-17T10:00:00+07:00', '2026-12-17T11:00:00+07:00', 'completed'),
	]);
	return byDay;
}

const meta = {
	title: 'booking-ui/BookingTimeGrid',
	component: BookingTimeGrid,
	tags: ['autodocs'],
	parameters: { layout: 'fullscreen' },
	args: {
		days: DAYS,
		bookingsByDay: makeBookingsByDay(),
		onSelectRange: () => {},
		onSelectBooking: () => {},
	},
} satisfies Meta<typeof BookingTimeGrid>;

export default meta;
type Story = StoryObj<typeof meta>;

function BookingTimeGridDemo(args: Story['args']) {
	const [selectedRange, setSelectedRange] = useState<TimeRange | null>(args?.selectedRange ?? null);
	const [selectedBookingId, setSelectedBookingId] = useState<string | undefined>(
		args?.selectedBookingId,
	);

	return (
		<div style={{ height: 600 }}>
			<BookingTimeGrid
				{...args}
				bookingsByDay={args?.bookingsByDay ?? makeBookingsByDay()}
				days={args?.days ?? DAYS}
				onSelectBooking={(booking) => {
					setSelectedBookingId(booking.id);
					setSelectedRange(null);
				}}
				onSelectRange={(range) => {
					setSelectedRange(range);
					setSelectedBookingId(undefined);
				}}
				selectedBookingId={selectedBookingId}
				selectedRange={selectedRange}
			/>
		</div>
	);
}

/** Drag on an empty part of a day column to select a range; click a booking block to select it instead. */
export const Default: Story = {
	render: (args) => <BookingTimeGridDemo {...args} />,
};

export const SingleDay: Story = {
	args: { days: ['2026-12-15'] },
	render: (args) => <BookingTimeGridDemo {...args} />,
};

/** Console's operator calendar — drag-to-select is disabled; booking blocks stay clickable. */
export const ReadOnly: Story = {
	args: { readOnly: true },
	render: (args) => <BookingTimeGridDemo {...args} />,
};

export const Empty: Story = {
	args: { bookingsByDay: new Map() },
	render: (args) => <BookingTimeGridDemo {...args} />,
};
