import {
	resetResourceTypesScenario,
	resourceTypesScenarioHandlers,
} from '@booking-core/api-client';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { renderWithQueryClient } from '../../test-utils';
import { SearchPage } from './SearchPage';

const server = setupServer(...resourceTypesScenarioHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
beforeEach(() => resetResourceTypesScenario());

function cardFor(resourceLabel: string): HTMLElement {
	const title = screen.getByText(resourceLabel);
	const card = title.closest('[data-slot="card"]');
	if (!card) throw new Error(`No card found for "${resourceLabel}"`);
	return card as HTMLElement;
}

describe('SearchPage', () => {
	it('shows a loading state before results arrive', () => {
		renderWithQueryClient(<SearchPage />);

		expect(document.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
	});

	it('shows every seeded resource with its own type’s custom field values', async () => {
		renderWithQueryClient(<SearchPage />);

		expect(await screen.findByText('Phone Booth 1')).toBeTruthy();
		expect(cardFor('Phone Booth 1').textContent).toContain('Has phone charger:Yes');
		expect(cardFor('Phone Booth 2').textContent).toContain('Has phone charger:No');
	});

	it('shows an empty state when nothing matches', async () => {
		server.use(http.get('*/resources', () => HttpResponse.json({ data: [], nextCursor: null })));
		renderWithQueryClient(<SearchPage />);

		expect(await screen.findByText('No resources match.')).toBeTruthy();
	});

	it('shows the error code when resources fail to load', async () => {
		server.use(
			http.get('*/resources', () =>
				HttpResponse.json(
					{ type: 'about:blank', title: 'Forbidden', status: 403, code: 'FORBIDDEN' },
					{ status: 403 },
				),
			),
		);
		renderWithQueryClient(<SearchPage />);

		expect(await screen.findByText("Couldn't load resources (FORBIDDEN).")).toBeTruthy();
	});

	it('narrows results to the selected resource type', async () => {
		const typeA = {
			id: 'type-a',
			key: 'type_a',
			label: 'Type A',
			version: 1,
			fields: [],
			createdAt: '2026-01-01T00:00:00Z',
			updatedAt: '2026-01-01T00:00:00Z',
		};
		const typeB = { ...typeA, id: 'type-b', key: 'type_b', label: 'Type B' };
		const resources = [
			{
				id: 'r1',
				resourceTypeId: 'type-a',
				siteId: 's1',
				label: 'Resource A1',
				customFieldValues: {},
				createdAt: '2026-01-01T00:00:00Z',
				updatedAt: '2026-01-01T00:00:00Z',
			},
			{
				id: 'r2',
				resourceTypeId: 'type-b',
				siteId: 's1',
				label: 'Resource B1',
				customFieldValues: {},
				createdAt: '2026-01-01T00:00:00Z',
				updatedAt: '2026-01-01T00:00:00Z',
			},
		];

		server.use(
			http.get('*/resource-types', () =>
				HttpResponse.json({ data: [typeA, typeB], nextCursor: null }),
			),
			http.get('*/resources', ({ request }) => {
				const resourceTypeId = new URL(request.url).searchParams.get('resourceTypeId');
				const filtered = resourceTypeId
					? resources.filter((r) => r.resourceTypeId === resourceTypeId)
					: resources;
				return HttpResponse.json({ data: filtered, nextCursor: null });
			}),
		);

		const user = userEvent.setup();
		renderWithQueryClient(<SearchPage />);

		expect(await screen.findByText('Resource A1')).toBeTruthy();
		expect(screen.getByText('Resource B1')).toBeTruthy();

		await user.click(screen.getByRole('combobox'));
		await user.click(await screen.findByRole('option', { name: 'Type B' }));

		await waitFor(() => expect(screen.queryByText('Resource A1')).toBeNull());
		expect(screen.getByText('Resource B1')).toBeTruthy();
	});
});
