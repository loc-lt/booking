import {
	type ResourceType,
	resetResourceTypesScenario,
	resourceTypesScenarioHandlers,
} from '@booking-core/api-client';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { renderWithQueryClient } from '../../test-utils';
import { ResourceTypeCard } from './ResourceTypeCard';

const server = setupServer(...resourceTypesScenarioHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
beforeEach(() => resetResourceTypesScenario());

const PHONE_BOOTH_TYPE: ResourceType = {
	id: '0193f4c2-7a3b-7c3e-8e2a-1f9b6c5d4e3a',
	key: 'phone_booth',
	label: 'Phone booth',
	version: 1,
	fields: [
		{ key: 'has_phone_charger', label: 'Has phone charger', type: 'boolean', required: true },
	],
	flowConfig: {
		confirmation: 'instant',
		checkIn: { required: true, opensMinutesBefore: 15, noShowAfterMinutes: 15 },
		cancellation: { allowedUntilMinutesBefore: 60 },
	},
	createdAt: '2026-10-28T09:00:00+07:00',
	updatedAt: '2026-10-28T09:00:00+07:00',
};

describe('ResourceTypeCard', () => {
	it('shows one input per the resource type’s own custom fields, and keeps Create disabled until Label is filled', async () => {
		const user = userEvent.setup();
		renderWithQueryClient(<ResourceTypeCard resourceType={PHONE_BOOTH_TYPE} />);

		await user.click(screen.getByRole('button', { name: 'Add resource' }));

		expect(screen.getByRole('checkbox', { name: /Has phone charger/ })).toBeTruthy();
		const createButton = screen.getByRole('button', {
			name: 'Create resource',
		}) as HTMLButtonElement;
		expect(createButton.disabled).toBe(true);

		await user.type(screen.getByLabelText('Label'), 'Phone Booth 4');
		expect(createButton.disabled).toBe(false);
	});

	it('adds the new resource to the list and resets the form on success', async () => {
		const user = userEvent.setup();
		renderWithQueryClient(<ResourceTypeCard resourceType={PHONE_BOOTH_TYPE} />);

		await user.click(screen.getByRole('button', { name: 'Add resource' }));
		await user.type(screen.getByLabelText('Label'), 'Phone Booth 4');
		await user.click(screen.getByRole('checkbox', { name: /Has phone charger/ }));
		await user.click(screen.getByRole('button', { name: 'Create resource' }));

		expect(await screen.findByText('Phone Booth 4')).toBeTruthy();
		expect((screen.getByLabelText('Label') as HTMLInputElement).value).toBe('');
	});
});
