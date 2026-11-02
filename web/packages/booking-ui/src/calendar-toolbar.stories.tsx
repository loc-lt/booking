import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import type { CalendarViewMode } from './calendar-navigation';
import { CalendarToolbar } from './calendar-toolbar';

const meta = {
	title: 'booking-ui/CalendarToolbar',
	component: CalendarToolbar,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		title: 'December 2026',
		viewMode: 'week',
		onPrevious: () => {},
		onNext: () => {},
		onToday: () => {},
		onViewModeChange: () => {},
	},
} satisfies Meta<typeof CalendarToolbar>;

export default meta;
type Story = StoryObj<typeof meta>;

function CalendarToolbarDemo(args: Story['args']) {
	const [viewMode, setViewMode] = useState<CalendarViewMode>(args?.viewMode ?? 'week');
	return (
		<CalendarToolbar
			{...args}
			onNext={args?.onNext ?? (() => {})}
			onPrevious={args?.onPrevious ?? (() => {})}
			onToday={args?.onToday ?? (() => {})}
			onViewModeChange={setViewMode}
			title={args?.title ?? 'December 2026'}
			viewMode={viewMode}
		/>
	);
}

export const Default: Story = {
	render: (args) => <CalendarToolbarDemo {...args} />,
};

export const DayView: Story = {
	args: { title: 'Tue, Dec 15 2026', viewMode: 'day' },
	render: (args) => <CalendarToolbarDemo {...args} />,
};

export const MonthView: Story = {
	args: { viewMode: 'month' },
	render: (args) => <CalendarToolbarDemo {...args} />,
};

export const CustomLabels: Story = {
	args: {
		viewModeLabels: { day: 'Daily', week: 'Weekly', month: 'Monthly' },
		todayLabel: "Today's date",
	},
	render: (args) => <CalendarToolbarDemo {...args} />,
};
