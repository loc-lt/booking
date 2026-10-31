import type { Meta, StoryObj } from '@storybook/react-vite';
import { CooldownButton } from './cooldown-button';

const meta = {
	title: 'common/CooldownButton',
	component: CooldownButton,
	tags: ['autodocs'],
	args: {
		children: 'Resend code',
		onClick: () => {},
	},
} satisfies Meta<typeof CooldownButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const ShortCooldown: Story = {
	args: { cooldownSeconds: 1 },
};
