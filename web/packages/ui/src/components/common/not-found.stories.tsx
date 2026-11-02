import type { Meta, StoryObj } from '@storybook/react-vite';
import { Button } from '../ui/button';
import { NotFound } from './not-found';

const meta = {
	title: 'common/NotFound',
	component: NotFound,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
} satisfies Meta<typeof NotFound>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Inline: Story = {
	args: { variant: 'inline' },
};

export const WithAction: Story = {
	args: {
		action: <Button>Back home</Button>,
	},
};

export const CustomCopy: Story = {
	args: {
		title: 'No bookings found',
		description: "This resource doesn't have any bookings yet.",
	},
};
