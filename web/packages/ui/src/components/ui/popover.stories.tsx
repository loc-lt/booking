import type { Meta, StoryObj } from '@storybook/react-vite';
import { Button } from './button';
import {
	Popover,
	PopoverContent,
	PopoverDescription,
	PopoverHeader,
	PopoverTitle,
	PopoverTrigger,
} from './popover';

const meta = {
	title: 'ui/Popover',
	component: Popover,
	tags: ['autodocs'],
	parameters: { layout: 'centered' },
} satisfies Meta<typeof Popover>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
	render: () => (
		<Popover>
			<PopoverTrigger render={<Button variant='outline'>Open popover</Button>} />
			<PopoverContent>
				<PopoverHeader>
					<PopoverTitle>Capacity</PopoverTitle>
					<PopoverDescription>This resource fits up to 8 people.</PopoverDescription>
				</PopoverHeader>
			</PopoverContent>
		</Popover>
	),
};
