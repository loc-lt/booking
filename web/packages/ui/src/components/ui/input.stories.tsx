import type { Meta, StoryObj } from '@storybook/react-vite';
import { Input } from './input';

const meta = {
	title: 'ui/Input',
	component: Input,
	tags: ['autodocs'],
	args: {
		placeholder: 'Type something…',
	},
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithValue: Story = {
	args: { defaultValue: 'Hot desk 3' },
};

export const Disabled: Story = {
	args: { disabled: true, defaultValue: 'Hot desk 3' },
};

export const Invalid: Story = {
	args: { 'aria-invalid': true, defaultValue: 'invalid value' },
};

export const NumberType: Story = {
	args: { type: 'number', placeholder: '0' },
};
