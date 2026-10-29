import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { renderWithQueryClient } from '../../test-utils';
import { ResourceAvailability } from './ResourceAvailability';

const SLOTS_RESPONSE = {
	siteId: 'site-1',
	resourceTypeId: 'type-1',
	date: '2026-12-15',
	slotMinutes: 30,
	slots: [
		{ start: '2026-12-15T09:00:00+07:00', end: '2026-12-15T09:30:00+07:00', resourceIds: ['r1'] },
		{ start: '2026-12-15T09:30:00+07:00', end: '2026-12-15T10:00:00+07:00', resourceIds: [] },
	],
};

const server = setupServer(http.get('*/availability', () => HttpResponse.json(SLOTS_RESPONSE)));

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('ResourceAvailability', () => {
	it('shows a loading state before slots arrive', () => {
		renderWithQueryClient(<ResourceAvailability resourceId='r1' resourceTypeId='type-1' />);

		expect(document.querySelector('[data-slot="skeleton"]')).toBeTruthy();
	});

	it('renders the resulting slots, free and taken', async () => {
		renderWithQueryClient(<ResourceAvailability resourceId='r1' resourceTypeId='type-1' />);

		expect(await screen.findByText(/9:00/)).toBeTruthy();
		const takenButton = screen.getByText(/9:30/).closest('button') as HTMLButtonElement;
		expect(takenButton.disabled).toBe(true);
	});

	it('lets a free slot be selected', async () => {
		const user = userEvent.setup();
		renderWithQueryClient(<ResourceAvailability resourceId='r1' resourceTypeId='type-1' />);

		const freeButton = (await screen.findByText(/9:00/)).closest('button') as HTMLButtonElement;
		const classNameBeforeSelection = freeButton.className;
		await user.click(freeButton);

		expect(freeButton.className).not.toBe(classNameBeforeSelection);
	});

	it('shows the error code when availability fails to load', async () => {
		server.use(
			http.get('*/availability', () =>
				HttpResponse.json(
					{ type: 'about:blank', title: 'Not found', status: 404, code: 'NOT_FOUND' },
					{ status: 404 },
				),
			),
		);
		renderWithQueryClient(<ResourceAvailability resourceId='r1' resourceTypeId='type-1' />);

		expect(await screen.findByText("Couldn't load availability (NOT_FOUND).")).toBeTruthy();
	});
});
