import {
	resetResourceTypesScenario,
	resourceTypesScenarioHandlers,
} from '@booking-core/api-client';
import { screen } from '@testing-library/react';
import { HttpResponse, http } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { renderWithQueryClient } from '../../test-utils';
import { ResourceTypesList } from './ResourceTypesList';

const server = setupServer(...resourceTypesScenarioHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
beforeEach(() => resetResourceTypesScenario());

describe('ResourceTypesList', () => {
	it('shows a loading state before the resource types arrive', () => {
		renderWithQueryClient(<ResourceTypesList />);

		expect(document.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
	});

	it('shows an empty state when the tenant has no resource types', async () => {
		server.use(
			http.get('*/resource-types', () => HttpResponse.json({ data: [], nextCursor: null })),
		);
		renderWithQueryClient(<ResourceTypesList />);

		expect(await screen.findByText('No resource types yet.')).toBeTruthy();
	});

	it('shows the error code when the list fails to load', async () => {
		server.use(
			http.get('*/resource-types', () =>
				HttpResponse.json(
					{ type: 'about:blank', title: 'Forbidden', status: 403, code: 'FORBIDDEN' },
					{ status: 403 },
				),
			),
		);
		renderWithQueryClient(<ResourceTypesList />);

		expect(await screen.findByText("Couldn't load resource types (FORBIDDEN).")).toBeTruthy();
	});

	it('lists the seeded resource types once loaded', async () => {
		renderWithQueryClient(<ResourceTypesList />);

		expect(await screen.findByText('Phone booth')).toBeTruthy();
	});
});
