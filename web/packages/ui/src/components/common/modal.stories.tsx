import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { Button } from '../ui/button';
import { Modal } from './modal';

const meta = {
	title: 'common/Modal',
	component: Modal,
	tags: ['autodocs'],
	parameters: { layout: 'centered' },
	args: {
		// Overridden by `ModalDemo`'s own state below — required here only so
		// the story satisfies the component's required props.
		open: false,
		onOpenChange: () => {},
		children: null,
	},
} satisfies Meta<typeof Modal>;

export default meta;
type Story = StoryObj<typeof meta>;

function ModalDemo() {
	const [open, setOpen] = useState(false);

	return (
		<Modal
			open={open}
			onOpenChange={setOpen}
			title='Edit resource'
			description="Change the resource's label and capacity."
			trigger={<Button>Open modal</Button>}
		>
			<p className='text-sm'>Arbitrary form content goes here.</p>
		</Modal>
	);
}

export const Default: Story = {
	render: () => <ModalDemo />,
};
