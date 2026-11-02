import type { Meta, StoryObj } from '@storybook/react-vite';
import { Avatar, AvatarFallback, AvatarGroup, AvatarImage } from './avatar';

const meta = {
	title: 'ui/Avatar',
	component: Avatar,
	tags: ['autodocs'],
} satisfies Meta<typeof Avatar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
	render: () => (
		<Avatar>
			<AvatarFallback>AC</AvatarFallback>
		</Avatar>
	),
};

export const BrokenImage: Story = {
	render: () => (
		<Avatar>
			<AvatarImage alt='Alex Chen' src='/does-not-exist.png' />
			<AvatarFallback>AC</AvatarFallback>
		</Avatar>
	),
};

export const Sizes: Story = {
	render: () => (
		<div className='flex items-center gap-4'>
			<Avatar size='sm'>
				<AvatarFallback>SM</AvatarFallback>
			</Avatar>
			<Avatar size='default'>
				<AvatarFallback>MD</AvatarFallback>
			</Avatar>
			<Avatar size='lg'>
				<AvatarFallback>LG</AvatarFallback>
			</Avatar>
		</div>
	),
};

export const Group: Story = {
	render: () => (
		<AvatarGroup>
			<Avatar>
				<AvatarFallback>AC</AvatarFallback>
			</Avatar>
			<Avatar>
				<AvatarFallback>PP</AvatarFallback>
			</Avatar>
			<Avatar>
				<AvatarFallback>JL</AvatarFallback>
			</Avatar>
		</AvatarGroup>
	),
};
