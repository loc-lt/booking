import type { Meta, StoryObj } from '@storybook/react-vite';
import { Button } from './button';
import {
	Card,
	CardAction,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from './card';

const meta = {
	title: 'ui/Card',
	component: Card,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Basic: Story = {
	render: () => (
		<Card className='w-80'>
			<CardHeader>
				<CardTitle>Meeting Room A</CardTitle>
				<CardDescription>2:00 PM – 4:30 PM</CardDescription>
			</CardHeader>
			<CardContent>
				<p className='text-muted-foreground text-sm'>Capacity: 8 people</p>
			</CardContent>
		</Card>
	),
};

export const WithActionAndFooter: Story = {
	render: () => (
		<Card className='w-80'>
			<CardHeader className='border-b'>
				<CardTitle>Pending approval</CardTitle>
				<CardAction>
					<Button size='sm' variant='ghost'>
						Dismiss
					</Button>
				</CardAction>
			</CardHeader>
			<CardContent>
				<p className='text-sm'>A member requested this resource for tomorrow at 9:00 AM.</p>
			</CardContent>
			<CardFooter className='justify-end gap-2'>
				<Button size='sm' variant='outline'>
					Reject
				</Button>
				<Button size='sm'>Approve</Button>
			</CardFooter>
		</Card>
	),
};
