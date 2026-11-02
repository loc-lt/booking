import type { AvailabilitySlot } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { AvailabilityGrid } from './availability-grid';

const RESOURCE_ID = '0193f4c4-3e7f-7a7c-ab6e-5d3f0a9b8c7d';

function makeSlots(count: number): AvailabilitySlot[] {
	return Array.from({ length: count }, (_, index) => {
		const hour = 9 + index;
		const start = `2026-12-15T${String(hour).padStart(2, '0')}:00:00+07:00`;
		const end = `2026-12-15T${String(hour).padStart(2, '0')}:30:00+07:00`;
		// Every third slot is fully booked, to show the disabled state.
		return { start, end, resourceIds: index % 3 === 2 ? [] : [RESOURCE_ID] };
	});
}

const SLOTS = makeSlots(9);

const meta = {
	title: 'booking-ui/AvailabilityGrid',
	component: AvailabilityGrid,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		slots: SLOTS,
	},
} satisfies Meta<typeof AvailabilityGrid>;

export default meta;
type Story = StoryObj<typeof meta>;

function AvailabilityGridDemo(args: Story['args']) {
	const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlot | undefined>();
	return (
		<AvailabilityGrid
			{...args}
			slots={args?.slots ?? SLOTS}
			selectedSlot={selectedSlot}
			onSelectSlot={setSelectedSlot}
		/>
	);
}

export const Default: Story = {
	render: (args) => <AvailabilityGridDemo {...args} />,
};

export const Empty: Story = {
	args: { slots: [] },
};
