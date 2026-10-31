import type { Meta, StoryObj } from '@storybook/react-vite';
import { Button } from './button';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from './dialog';

const meta = {
	title: 'ui/Dialog',
	component: Dialog,
	tags: ['autodocs'],
	parameters: { layout: 'centered' },
} satisfies Meta<typeof Dialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
	render: () => (
		<Dialog>
			<DialogTrigger render={<Button>Open dialog</Button>} />
			<DialogContent>
				<DialogHeader>
					<DialogTitle>Edit resource</DialogTitle>
					<DialogDescription>Change the resource's label and capacity.</DialogDescription>
				</DialogHeader>
				<DialogFooter>
					<Button variant='outline'>Cancel</Button>
					<Button>Save</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	),
};
