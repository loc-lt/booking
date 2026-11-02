import type { Meta, StoryObj } from '@storybook/react-vite';
import { Button } from './button';
import {
	Sheet,
	SheetClose,
	SheetContent,
	SheetDescription,
	SheetFooter,
	SheetHeader,
	SheetTitle,
	SheetTrigger,
} from './sheet';

const meta = {
	title: 'ui/Sheet',
	component: Sheet,
	tags: ['autodocs'],
} satisfies Meta<typeof Sheet>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
	render: () => (
		<Sheet>
			<SheetTrigger render={<Button>Open sheet</Button>} />
			<SheetContent>
				<SheetHeader>
					<SheetTitle>Edit resource</SheetTitle>
					<SheetDescription>Change the resource's label and capacity.</SheetDescription>
				</SheetHeader>
				<SheetFooter>
					<SheetClose render={<Button variant='outline'>Cancel</Button>} />
					<Button>Save</Button>
				</SheetFooter>
			</SheetContent>
		</Sheet>
	),
};

export const FromLeft: Story = {
	render: () => (
		<Sheet>
			<SheetTrigger render={<Button variant='outline'>Open from left</Button>} />
			<SheetContent side='left'>
				<SheetHeader>
					<SheetTitle>Filters</SheetTitle>
					<SheetDescription>Narrow down the bookings list.</SheetDescription>
				</SheetHeader>
			</SheetContent>
		</Sheet>
	),
};
