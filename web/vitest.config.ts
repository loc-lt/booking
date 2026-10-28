import { defineConfig } from 'vitest/config';

export default defineConfig({
	test: {
		passWithNoTests: true,
		environment: 'jsdom',
		setupFiles: ['./vitest.setup.ts'],
		include: ['packages/*/src/**/*.{test,spec}.{ts,tsx}', 'apps/*/src/**/*.{test,spec}.{ts,tsx}'],
	},
});
