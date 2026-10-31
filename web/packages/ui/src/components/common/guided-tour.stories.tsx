import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { Button } from '../ui/button';
import { GuidedTour, type GuidedTourStep } from './guided-tour';

const STEPS: GuidedTourStep[] = [
	{
		id: 'welcome',
		title: 'Welcome to the console',
		content: 'This short tour walks through the approvals and bookings screens.',
		target: null,
	},
	{
		id: 'approvals',
		title: 'Approvals',
		content: 'Pending bookings that need a yes or no show up here first.',
		target: null,
	},
	{
		id: 'bookings',
		title: 'Bookings',
		content: "Every booking, confirmed or not, lives here once it's been decided.",
		target: null,
	},
];

const meta = {
	title: 'common/GuidedTour',
	component: GuidedTour,
	tags: ['autodocs'],
	parameters: { layout: 'fullscreen' },
	args: {
		steps: STEPS,
		// Overridden by `GuidedTourDemo`'s own state below — required here only
		// so every story satisfies the component's required props.
		open: false,
		onOpenChange: () => {},
	},
} satisfies Meta<typeof GuidedTour>;

export default meta;
type Story = StoryObj<typeof meta>;

function GuidedTourDemo(args: Story['args']) {
	const [open, setOpen] = useState(true);

	return (
		<div className='flex min-h-screen items-center justify-center'>
			<Button onClick={() => setOpen(true)}>Restart tour</Button>
			<GuidedTour {...args} steps={args?.steps ?? STEPS} open={open} onOpenChange={setOpen} />
		</div>
	);
}

export const Default: Story = {
	render: (args) => <GuidedTourDemo {...args} />,
};
