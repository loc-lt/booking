import type { Meta, StoryObj } from '@storybook/react-vite';
import { AppLoading, PageLoading } from './loading';

const meta = {
	title: 'layout/Loading',
	component: PageLoading,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
} satisfies Meta<typeof PageLoading>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Compact loading state for content rendered inside an already-mounted `AppShell`. */
export const Page: Story = {};

export const PageWithCustomLabel: Story = {
	args: { label: 'Loading bookings…' },
};

/** Full-screen loading state, for routes with no layout shell mounted above them yet. */
export const FullScreen: Story = {
	parameters: { layout: 'fullscreen' },
	render: (args) => <AppLoading {...args} />,
};
