import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest';
import type { ResourceList } from '../generated/models';
import { resetResourceTypesScenario, resourceTypesScenarioHandlers } from './resourceTypesStore';

const server = setupServer(...resourceTypesScenarioHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
beforeEach(() => resetResourceTypesScenario());

describe('resourceTypesScenarioHandlers', () => {
	it('rejects creating a resource type with a key already in use', async () => {
		const response = await fetch('http://localhost/resource-types', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ key: 'phone_booth', label: 'Another phone booth', fields: [] }),
		});

		expect(response.status).toBe(422);
		const body = await response.json();
		expect(body.code).toBe('VALIDATION_FAILED');
		expect(body.errors).toEqual([
			{ field: 'key', message: 'Key is already used by another resource type.' },
		]);
	});

	it('404s when creating a resource for a resource type that does not exist', async () => {
		const response = await fetch('http://localhost/resources', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				resourceTypeId: '00000000-0000-7000-8000-000000000000',
				siteId: '00000000-0000-7000-8000-000000000001',
				label: 'Ghost resource',
			}),
		});

		expect(response.status).toBe(404);
		const body = await response.json();
		expect(body.code).toBe('NOT_FOUND');
	});

	it('filters resources by resourceTypeId', async () => {
		const seededTypeId = '0193f4c2-7a3b-7c3e-8e2a-1f9b6c5d4e3a';

		const matching = await fetch(`http://localhost/resources?resourceTypeId=${seededTypeId}`);
		const matchingBody: ResourceList = await matching.json();
		expect(matchingBody.data.length).toBe(3);

		const unknownTypeId = '00000000-0000-7000-8000-000000000002';
		const nonMatching = await fetch(`http://localhost/resources?resourceTypeId=${unknownTypeId}`);
		const nonMatchingBody: ResourceList = await nonMatching.json();
		expect(nonMatchingBody.data).toEqual([]);
	});
});
