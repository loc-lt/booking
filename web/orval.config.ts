import { defineConfig } from 'orval';

export default defineConfig({
	bookingCore: {
		input: '../contracts/openapi.yaml',
		output: {
			target: 'packages/api-client/src/generated/endpoints',
			schemas: 'packages/api-client/src/generated/models',
			client: 'react-query',
			mode: 'tags-split',
			clean: true,
			prettier: true,
			mock: {
				type: 'msw',
				useExamples: true,
			},
			override: {
				mutator: {
					path: 'packages/api-client/src/client.ts',
					name: 'apiFetch',
				},
			},
		},
	},
	bookingCoreZod: {
		input: '../contracts/openapi.yaml',
		output: {
			target: 'packages/api-client/src/generated/zod/index.ts',
			client: 'zod',
			mode: 'single',
			clean: true,
			prettier: true,
		},
	},
});
