import type { FieldDefinition } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { BookingCreatePanel } from './booking-create-panel';
import type { TimeRange } from './booking-occupancy';

const FIELDS: FieldDefinition[] = [
	{ key: 'attendees', label: 'Attendees', type: 'number', required: true },
	{ key: 'hasProjector', label: 'Needs a projector', type: 'boolean' },
];

const INITIAL_RANGE: TimeRange = {
	start: '2026-12-15T14:00:00+07:00',
	end: '2026-12-15T15:00:00+07:00',
};

const meta = {
	title: 'booking-ui/BookingCreatePanel',
	component: BookingCreatePanel,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		bookingsByDay: new Map(),
		fields: FIELDS,
		initialRange: INITIAL_RANGE,
		onRangeChange: () => {},
		onSubmit: () => {},
		onValuesChange: () => {},
		values: {},
	},
} satisfies Meta<typeof BookingCreatePanel>;

export default meta;
type Story = StoryObj<typeof meta>;

function BookingCreatePanelDemo(args: Story['args']) {
	const [values, setValues] = useState<Record<string, unknown>>(args?.values ?? {});
	return (
		<BookingCreatePanel
			{...args}
			bookingsByDay={args?.bookingsByDay ?? new Map()}
			fields={args?.fields ?? FIELDS}
			initialRange={args?.initialRange ?? INITIAL_RANGE}
			onRangeChange={args?.onRangeChange ?? (() => {})}
			onSubmit={args?.onSubmit ?? (() => {})}
			onValuesChange={setValues}
			values={values}
		/>
	);
}

export const Default: Story = {
	render: (args) => <BookingCreatePanelDemo {...args} />,
};

export const Submitting: Story = {
	args: { isSubmitting: true },
	render: (args) => <BookingCreatePanelDemo {...args} />,
};

export const FieldErrors: Story = {
	args: { fieldErrors: { attendees: 'Must be at least 1.' } },
	render: (args) => <BookingCreatePanelDemo {...args} />,
};

/** A denial from the caller's own mutation, e.g. `SLOT_TAKEN` or a `BOOKING_DENIED` reason. */
export const DeniedByRule: Story = {
	args: {
		error: <p className='text-destructive text-sm'>This resource cannot be booked before 9am.</p>,
	},
	render: (args) => <BookingCreatePanelDemo {...args} />,
};
