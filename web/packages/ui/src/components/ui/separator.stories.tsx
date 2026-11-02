import type { Meta, StoryObj } from '@storybook/react-vite';
import { Separator } from './separator';

const meta = {
	title: 'ui/Separator',
	component: Separator,
	tags: ['autodocs'],
} satisfies Meta<typeof Separator>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Horizontal: Story = {
	render: () => (
		<div className='w-64'>
			<p className='text-sm'>Resource types</p>
			<Separator className='my-3' />
			<p className='text-sm'>Approvals</p>
		</div>
	),
};

export const Vertical: Story = {
	render: () => (
		<div className='flex h-8 items-center gap-3'>
			<span className='text-sm'>Bookings</span>
			<Separator orientation='vertical' />
			<span className='text-sm'>Approvals</span>
		</div>
	),
};
