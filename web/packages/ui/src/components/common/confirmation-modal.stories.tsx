import type { Meta, StoryObj } from '@storybook/react-vite';
import { type ComponentProps, useState } from 'react';
import { Button } from '../ui/button';
import { ConfirmationModal } from './confirmation-modal';

const meta = {
	title: 'common/ConfirmationModal',
	component: ConfirmationModal,
	tags: ['autodocs'],
	parameters: { layout: 'centered' },
	args: {
		cancelLabel: 'Keep booking',
		confirmLabel: 'Cancel booking',
		title: 'Cancel booking?',
		description: 'The member will need to book again if they still need the resource.',
		dangerous: true,
		// Overridden by `ConfirmationModalDemo`'s own state below — required
		// here only so every story satisfies the component's required props.
		open: false,
		onOpenChange: () => {},
		onConfirm: () => {},
	},
} satisfies Meta<typeof ConfirmationModal>;

export default meta;
type Story = StoryObj<typeof meta>;

function ConfirmationModalDemo(args: ComponentProps<typeof ConfirmationModal>) {
	const [open, setOpen] = useState(false);

	return (
		<>
			<Button variant='outline' onClick={() => setOpen(true)}>
				Cancel booking
			</Button>
			<ConfirmationModal
				{...args}
				open={open}
				onOpenChange={setOpen}
				onConfirm={() => setOpen(false)}
			/>
		</>
	);
}

export const Dangerous: Story = {
	render: (args) => <ConfirmationModalDemo {...args} />,
};

export const NonDangerous: Story = {
	args: {
		cancelLabel: 'Cancel',
		confirmLabel: 'Approve',
		title: 'Approve booking?',
		description: undefined,
		dangerous: false,
	},
	render: (args) => <ConfirmationModalDemo {...args} />,
};

export const Confirming: Story = {
	args: {
		isConfirming: true,
	},
	render: (args) => <ConfirmationModalDemo {...args} />,
};
