import type { Meta, StoryObj } from '@storybook/react-vite';
import { Search } from './search';

const meta = {
	title: 'common/Search',
	component: Search,
	tags: ['autodocs'],
	args: {
		className: 'w-72',
		onValueChange: () => {},
	},
} satisfies Meta<typeof Search>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {};

export const WithValue: Story = {
	args: { defaultValue: 'Meeting Room A' },
};

export const Disabled: Story = {
	args: { disabled: true, defaultValue: 'Meeting Room A' },
};
