import {
	resetResourceTypesScenario,
	resourceTypesScenarioHandlers,
} from '@booking-core/api-client';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import { renderWithQueryClient } from '../../test-utils';
import { CreateResourceTypeForm } from './CreateResourceTypeForm';

const server = setupServer(...resourceTypesScenarioHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
beforeEach(() => resetResourceTypesScenario());

describe('CreateResourceTypeForm', () => {
	it('blocks submit and shows validation messages when label and key are empty', async () => {
		const user = userEvent.setup();
		renderWithQueryClient(<CreateResourceTypeForm />);

		await user.click(screen.getByRole('button', { name: 'Create resource type' }));

		expect(await screen.findByText('Label is required')).toBeTruthy();
		expect(screen.getByText('Key is required')).toBeTruthy();
	});

	it('surfaces a duplicate key as an error on the Key field, not a generic banner', async () => {
		const user = userEvent.setup();
		renderWithQueryClient(<CreateResourceTypeForm />);

		await user.type(screen.getByLabelText('Label'), 'Another phone booth');
		await user.type(screen.getByLabelText('Key'), 'phone_booth');
		await user.click(screen.getByRole('button', { name: 'Create resource type' }));

		expect(await screen.findByText('Key is already used by another resource type.')).toBeTruthy();
		expect(screen.queryByText(/Couldn't create the resource type/)).toBeNull();
	});

	it('resets the form after a successful create', async () => {
		const user = userEvent.setup();
		renderWithQueryClient(<CreateResourceTypeForm />);

		await user.type(screen.getByLabelText('Label'), 'Meeting Room');
		await user.type(screen.getByLabelText('Key'), 'meeting_room');
		await user.click(screen.getByRole('button', { name: 'Create resource type' }));

		await waitFor(() => {
			expect((screen.getByLabelText('Label') as HTMLInputElement).value).toBe('');
		});
		expect((screen.getByLabelText('Key') as HTMLInputElement).value).toBe('');
	});
});
