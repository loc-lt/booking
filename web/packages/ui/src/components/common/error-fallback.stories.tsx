import type { Meta, StoryObj } from '@storybook/react-vite';
import { ErrorFallback } from './error-fallback';

const meta = {
	title: 'common/ErrorFallback',
	component: ErrorFallback,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		error: new Error('Could not reach the booking service.'),
		onRetry: () => {},
	},
} satisfies Meta<typeof ErrorFallback>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Inline: Story = {
	args: { variant: 'inline' },
};

export const StringError: Story = {
	args: { error: 'Something went wrong' },
};

export const UnknownError: Story = {
	args: { error: undefined },
};
