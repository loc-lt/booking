import type { Meta, StoryObj } from '@storybook/react-vite';
import { IconButton } from './icon-button';

const meta = {
	title: 'common/IconButton',
	component: IconButton,
	tags: ['autodocs'],
	args: {
		icon: 'Pencil',
		label: 'Edit',
	},
} satisfies Meta<typeof IconButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Ghost: Story = {
	args: { variant: 'ghost' },
};

export const Destructive: Story = {
	args: { icon: 'Trash', label: 'Delete', variant: 'destructive' },
};

export const Disabled: Story = {
	args: { disabled: true },
};
