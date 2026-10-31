import type { Meta, StoryObj } from '@storybook/react-vite';
import { Icon } from './icon';

const meta = {
	title: 'common/Icon',
	component: Icon,
	tags: ['autodocs'],
	args: {
		name: 'Calendar',
	},
} satisfies Meta<typeof Icon>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Loading: Story = {
	args: { isLoading: true },
};

export const Large: Story = {
	args: { className: 'size-8' },
};
