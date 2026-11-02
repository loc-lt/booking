import type { Booking, BookingStatus } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { BookingMonthGrid } from './booking-month-grid';

const RESOURCE_ID = '0193f4c4-3e7f-7a7c-ab6e-5d3f0a9b8c7d';
const RESOURCE_TYPE_ID = '0193f4c4-2d6e-7f6b-ba5d-4c2e9f8a7b6c';
const SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';
const MEMBER_ID = '0193f4c5-4f80-7b8d-bc7f-6e4a1b0c9d8e';

function makeBooking(id: string, start: string, status: BookingStatus): Booking {
	return {
		id,
		resourceId: RESOURCE_ID,
		resourceTypeId: RESOURCE_TYPE_ID,
		siteId: SITE_ID,
		memberId: MEMBER_ID,
		start,
		end: start,
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
		makeBooking('a', '2026-12-15T09:00:00+07:00', 'confirmed'),
		makeBooking('b', '2026-12-15T14:00:00+07:00', 'pending_approval'),
	]);
	byDay.set('2026-12-17', [makeBooking('c', '2026-12-17T10:00:00+07:00', 'completed')]);
	// More bookings than `maxPillsPerDay` — shows the "+N more" overflow label.
	byDay.set('2026-12-22', [
		makeBooking('d', '2026-12-22T08:00:00+07:00', 'confirmed'),
		makeBooking('e', '2026-12-22T10:00:00+07:00', 'confirmed'),
		makeBooking('f', '2026-12-22T13:00:00+07:00', 'pending_approval'),
		makeBooking('g', '2026-12-22T15:00:00+07:00', 'confirmed'),
	]);
	return byDay;
}

const meta = {
	title: 'booking-ui/BookingMonthGrid',
	component: BookingMonthGrid,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		referenceDate: '2026-12-15',
		bookingsByDay: makeBookingsByDay(),
		onNavigateMonth: () => {},
		onSelectBooking: () => {},
		onSelectDay: (_day: string) => {},
	},
} satisfies Meta<typeof BookingMonthGrid>;

export default meta;
type Story = StoryObj<typeof meta>;

function BookingMonthGridDemo(args: Story['args']) {
	const [referenceDate, setReferenceDate] = useState(args?.referenceDate ?? '2026-12-15');
	return (
		<div style={{ height: 600 }}>
			<BookingMonthGrid
				{...args}
				bookingsByDay={args?.bookingsByDay ?? makeBookingsByDay()}
				onNavigateMonth={(direction) => {
					const [year, month] = referenceDate.split('-').map(Number);
					const next = new Date(year ?? 0, (month ?? 1) - 1 + direction, 15);
					setReferenceDate(
						`${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-15`,
					);
				}}
				onSelectBooking={args?.onSelectBooking ?? (() => {})}
				referenceDate={referenceDate}
			/>
		</div>
	);
}

export const Default: Story = {
	render: (args) => <BookingMonthGridDemo {...args} />,
};

export const Empty: Story = {
	args: { bookingsByDay: new Map() },
	render: (args) => <BookingMonthGridDemo {...args} />,
};

/** Omitting `onSelectDay` makes the grid look-only — no hover affordance, no click handler on empty cells. */
export const LookOnly: Story = {
	args: { onSelectDay: undefined },
	render: (args) => <BookingMonthGridDemo {...args} />,
};

export const DrillIntoDay: Story = {
	args: { onSelectDay: (day: string) => alert(`Drilled into ${day}`) },
	render: (args) => <BookingMonthGridDemo {...args} />,
};
