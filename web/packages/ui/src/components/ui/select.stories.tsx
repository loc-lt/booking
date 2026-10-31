import type { Meta, StoryObj } from '@storybook/react-vite';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './select';

const RESOURCE_TYPES = [
	{ value: 'hot-desk', label: 'Hot desk' },
	{ value: 'meeting-room', label: 'Meeting room' },
	{ value: 'phone-booth', label: 'Phone booth' },
];

const meta = {
	title: 'ui/Select',
	component: Select,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
} satisfies Meta<typeof Select>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
	render: () => (
		<Select defaultValue='meeting-room'>
			<SelectTrigger className='w-56'>
				<SelectValue placeholder='Select a resource type' />
			</SelectTrigger>
			<SelectContent>
				{RESOURCE_TYPES.map((type) => (
					<SelectItem key={type.value} value={type.value}>
						{type.label}
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	),
};

export const Small: Story = {
	render: () => (
		<Select defaultValue='hot-desk'>
			<SelectTrigger className='w-56' size='sm'>
				<SelectValue />
			</SelectTrigger>
			<SelectContent>
				{RESOURCE_TYPES.map((type) => (
					<SelectItem key={type.value} value={type.value}>
						{type.label}
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	),
};

export const Disabled: Story = {
	render: () => (
		<Select defaultValue='hot-desk' disabled>
			<SelectTrigger className='w-56'>
				<SelectValue />
			</SelectTrigger>
			<SelectContent>
				{RESOURCE_TYPES.map((type) => (
					<SelectItem key={type.value} value={type.value}>
						{type.label}
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	),
};
