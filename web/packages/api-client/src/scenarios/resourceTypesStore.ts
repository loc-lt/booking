import { delay, HttpResponse, http } from 'msw';
import type {
	CreateResourceRequest,
	CreateResourceTypeRequest,
	UpdateResourceTypeRequest,
} from '../generated/models';
import {
	createResourceOp,
	createResourceTypeOp,
	getResourceOp,
	getResourceTypeOp,
	listResourcesOp,
	listResourceTypesOp,
	resetResourceTypesState,
	updateResourceTypeOp,
} from './resourceTypesOperations';

/**
 * In-browser MSW adapter over resourceTypesOperations.ts, for solo dev (one
 * tab, mocks reset on reload) and tests. For a shared backend across apps,
 * see mock-server/, which calls the same operations over real HTTP.
 */

/** Restores the seeded resource types and resources. Call between tests. */
export function resetResourceTypesScenario(): void {
	resetResourceTypesState();
}

function json(result: { status: number; body: unknown }) {
	return HttpResponse.json(result.body as Parameters<typeof HttpResponse.json>[0], {
		status: result.status,
	});
}

export const resourceTypesScenarioHandlers = [
	http.get('*/resource-types', async () => {
		await delay(300);
		return json(listResourceTypesOp());
	}),

	http.post('*/resource-types', async ({ request }) => {
		const requestBody = (await request.json()) as CreateResourceTypeRequest;
		await delay(300);
		return json(createResourceTypeOp(requestBody));
	}),

	http.get('*/resource-types/:resourceTypeId', async ({ params }) => {
		await delay(300);
		return json(getResourceTypeOp(params.resourceTypeId as string));
	}),

	http.patch('*/resource-types/:resourceTypeId', async ({ params, request }) => {
		const requestBody = (await request.json()) as UpdateResourceTypeRequest;
		await delay(300);
		return json(updateResourceTypeOp(params.resourceTypeId as string, requestBody));
	}),

	http.get('*/resources', async ({ request }) => {
		await delay(300);
		const url = new URL(request.url);
		return json(
			listResourcesOp({
				resourceTypeId: url.searchParams.get('resourceTypeId'),
				siteId: url.searchParams.get('siteId'),
			}),
		);
	}),

	http.post('*/resources', async ({ request }) => {
		const requestBody = (await request.json()) as CreateResourceRequest;
		await delay(300);
		return json(createResourceOp(requestBody));
	}),

	http.get('*/resources/:resourceId', async ({ params }) => {
		await delay(300);
		return json(getResourceOp(params.resourceId as string));
	}),
];
