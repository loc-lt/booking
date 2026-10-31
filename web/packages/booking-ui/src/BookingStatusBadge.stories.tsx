import { BookingStatus } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { BookingStatusBadge } from './BookingStatusBadge';

const meta = {
	title: 'booking-ui/BookingStatusBadge',
	component: BookingStatusBadge,
	tags: ['autodocs'],
	argTypes: {
		status: {
			control: 'select',
			options: Object.values(BookingStatus),
		},
	},
} satisfies Meta<typeof BookingStatusBadge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const PendingApproval: Story = {
	args: { status: BookingStatus.pending_approval },
};

export const Confirmed: Story = {
	args: { status: BookingStatus.confirmed },
};

export const CheckedIn: Story = {
	args: { status: BookingStatus.checked_in },
};

export const Cancelled: Story = {
	args: { status: BookingStatus.cancelled },
};

export const NoShow: Story = {
	args: { status: BookingStatus.no_show },
};

export const CustomLabel: Story = {
	args: {
		status: BookingStatus.pending_approval,
		labels: { [BookingStatus.pending_approval]: 'Awaiting manager' },
	},
};
