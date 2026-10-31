import type { Meta, StoryObj } from '@storybook/react-vite';
import { Button } from './button';

const meta = {
	title: 'ui/Button',
	component: Button,
	tags: ['autodocs'],
	argTypes: {
		variant: {
			control: 'select',
			options: ['default', 'outline', 'secondary', 'ghost', 'destructive', 'link'],
		},
		size: {
			control: 'select',
			options: ['default', 'xs', 'sm', 'lg', 'icon', 'icon-xs', 'icon-sm', 'icon-lg'],
		},
	},
	args: {
		children: 'Button',
		disabled: false,
	},
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Outline: Story = {
	args: { variant: 'outline' },
};

export const Secondary: Story = {
	args: { variant: 'secondary' },
};

export const Ghost: Story = {
	args: { variant: 'ghost' },
};

export const Destructive: Story = {
	args: { variant: 'destructive' },
};

export const Link: Story = {
	args: { variant: 'link' },
};

export const Disabled: Story = {
	args: { disabled: true },
};
