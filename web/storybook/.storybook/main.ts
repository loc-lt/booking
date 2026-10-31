import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import type { StorybookConfig } from '@storybook/react-vite';
import { mergeConfig } from 'vite';

const config: StorybookConfig = {
	stories: [
		'../../packages/*/src/**/*.stories.@(ts|tsx)',
		'../../apps/*/src/**/*.stories.@(ts|tsx)',
	],
	addons: ['msw-storybook-addon'],
	framework: {
		name: '@storybook/react-vite',
		options: {},
	},
	staticDirs: ['../public'],
	viteFinal: (viteConfig) =>
		mergeConfig(viteConfig, {
			plugins: [react(), tailwindcss()],
		}),
};

export default config;
