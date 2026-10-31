import type { Meta, StoryObj } from '@storybook/react-vite';
import { RefreshButton } from './refresh-button';

const meta = {
	title: 'common/RefreshButton',
	component: RefreshButton,
	tags: ['autodocs'],
	args: {
		onClick: () => {},
	},
} satisfies Meta<typeof RefreshButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const IconOnly: Story = {
	args: { showLabel: false },
};

export const Disabled: Story = {
	args: { disabled: true },
};
