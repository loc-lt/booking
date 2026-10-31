import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { Calendar } from './calendar';

const meta = {
	title: 'ui/Calendar',
	component: Calendar,
	tags: ['autodocs'],
	parameters: { layout: 'centered' },
} satisfies Meta<typeof Calendar>;

export default meta;
type Story = StoryObj<typeof meta>;

function CalendarDemo() {
	const [selected, setSelected] = useState<Date | undefined>(new Date(2026, 11, 15));
	return <Calendar mode='single' selected={selected} onSelect={setSelected} />;
}

export const Default: Story = {
	render: () => <CalendarDemo />,
};
