import type { Meta, StoryObj } from '@storybook/react-vite';
import { CircleUserRound } from 'lucide-react';
import { ProfileMenu } from './profile-menu';

const meta = {
	title: 'apps/console/ProfileMenu',
	component: ProfileMenu,
	tags: ['autodocs'],
	args: {
		user: { name: 'Alex Chen', caption: 'alex.chen@example.com' },
	},
} satisfies Meta<typeof ProfileMenu>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithSignOut: Story = {
	args: { onSignOut: () => {} },
};

export const SigningOut: Story = {
	args: { onSignOut: () => {}, isSigningOut: true },
};

export const WithExtraItems: Story = {
	args: {
		items: [
			{ key: 'profile', label: 'View profile', icon: <CircleUserRound />, onSelect: () => {} },
		],
		onSignOut: () => {},
	},
};

export const SingleNameInitial: Story = {
	args: {
		user: { name: 'Madonna' },
	},
};
