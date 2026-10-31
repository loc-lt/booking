import type { Meta, StoryObj } from '@storybook/react-vite';
import { Skeleton } from './skeleton';

const meta = {
	title: 'ui/Skeleton',
	component: Skeleton,
	tags: ['autodocs'],
	args: {
		className: 'h-9 w-64',
	},
} satisfies Meta<typeof Skeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const RowStack: Story = {
	render: () => (
		<div className='flex flex-col gap-2'>
			<Skeleton className='h-16 w-80' />
			<Skeleton className='h-16 w-80' />
			<Skeleton className='h-16 w-80' />
		</div>
	),
};
