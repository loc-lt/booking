import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { ThemeSwitcher, type ThemeSwitcherProps } from './theme-switcher';

const meta = {
	title: 'selects/ThemeSwitcher',
	component: ThemeSwitcher,
	tags: ['autodocs'],
	args: {
		theme: 'light',
		onThemeChange: () => {},
	},
} satisfies Meta<typeof ThemeSwitcher>;

export default meta;
type Story = StoryObj<typeof meta>;

function ThemeSwitcherDemo({ theme: initialTheme, labels }: ThemeSwitcherProps) {
	const [theme, setTheme] = useState(initialTheme);

	return <ThemeSwitcher labels={labels} theme={theme} onThemeChange={setTheme} />;
}

export const Light: Story = {
	render: (args) => <ThemeSwitcherDemo {...args} />,
};

export const Dark: Story = {
	args: { theme: 'dark' },
	render: (args) => <ThemeSwitcherDemo {...args} />,
};

export const System: Story = {
	args: { theme: 'system' },
	render: (args) => <ThemeSwitcherDemo {...args} />,
};

export const CustomLabels: Story = {
	args: {
		labels: { trigger: 'Switch theme', dark: 'Night', light: 'Day', system: 'Auto' },
	},
	render: (args) => <ThemeSwitcherDemo {...args} />,
};
