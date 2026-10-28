import { delay, HttpResponse, http } from 'msw';
import type {
	CreateResourceRequest,
	CreateResourceTypeRequest,
	FieldError,
	Resource,
	ResourceType,
} from '../generated/models';

/**
 * Stateful mock backend for resource types and resources, kept in memory for
 * the life of the tab. The default Orval-generated handlers return random or
 * canned data on every call, which can't demo "admin creates a type, member
 * sees it" — this scenario actually stores what's created.
 */

const DEMO_SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';
const PHONE_BOOTH_TYPE_ID = '0193f4c2-7a3b-7c3e-8e2a-1f9b6c5d4e3a';

function seedResourceTypes(): ResourceType[] {
	return [
		{
			id: PHONE_BOOTH_TYPE_ID,
			key: 'phone_booth',
			label: 'Phone booth',
			version: 1,
			fields: [
				{
					key: 'has_phone_charger',
					label: 'Has phone charger',
					type: 'boolean',
					required: true,
				},
			],
			flowConfig: {
				confirmation: 'instant',
				checkIn: { required: true, opensMinutesBefore: 15, noShowAfterMinutes: 15 },
				cancellation: { allowedUntilMinutesBefore: 60 },
			},
			createdAt: '2026-10-28T09:00:00+07:00',
			updatedAt: '2026-10-28T09:00:00+07:00',
		},
	];
}

function seedResources(): Resource[] {
	return [
		{
			id: '0193f4c2-9c5d-7e5a-af4c-3b1d8e7f6a5c',
			resourceTypeId: PHONE_BOOTH_TYPE_ID,
			siteId: DEMO_SITE_ID,
			label: 'Phone Booth 1',
			customFieldValues: { has_phone_charger: true },
			createdAt: '2026-10-28T09:05:00+07:00',
			updatedAt: '2026-10-28T09:05:00+07:00',
		},
		{
			id: '0193f4c3-0a1b-7f2c-8d3e-4c2e9f8a7b6d',
			resourceTypeId: PHONE_BOOTH_TYPE_ID,
			siteId: DEMO_SITE_ID,
			label: 'Phone Booth 2',
			customFieldValues: { has_phone_charger: false },
			createdAt: '2026-10-28T09:05:00+07:00',
			updatedAt: '2026-10-28T09:05:00+07:00',
		},
		{
			id: '0193f4c3-1b2c-7a3d-9e4f-5d3f0a9b8c7e',
			resourceTypeId: PHONE_BOOTH_TYPE_ID,
			siteId: DEMO_SITE_ID,
			label: 'Phone Booth 3',
			customFieldValues: { has_phone_charger: true },
			createdAt: '2026-10-28T09:05:00+07:00',
			updatedAt: '2026-10-28T09:05:00+07:00',
		},
	];
}

let resourceTypes = seedResourceTypes();
let resources = seedResources();

/** Restores the seeded resource types and resources. Call between tests. */
export function resetResourceTypesScenario(): void {
	resourceTypes = seedResourceTypes();
	resources = seedResources();
}

function validationFailed(errors: FieldError[]) {
	return HttpResponse.json(
		{
			type: 'about:blank',
			title: 'Validation failed',
			status: 422,
			code: 'VALIDATION_FAILED',
			errors,
		},
		{ status: 422 },
	);
}

function notFound(detail: string) {
	return HttpResponse.json(
		{ type: 'about:blank', title: 'Not found', status: 404, code: 'NOT_FOUND', detail },
		{ status: 404 },
	);
}

export const resourceTypesScenarioHandlers = [
	http.get('*/resource-types', async () => {
		await delay(300);
		return HttpResponse.json({ data: resourceTypes, nextCursor: null });
	}),

	http.post('*/resource-types', async ({ request }) => {
		const body = (await request.json()) as CreateResourceTypeRequest;
		await delay(300);

		if (resourceTypes.some((type) => type.key === body.key)) {
			return validationFailed([
				{ field: 'key', message: 'Key is already used by another resource type.' },
			]);
		}

		const now = new Date().toISOString();
		const created: ResourceType = {
			id: crypto.randomUUID(),
			key: body.key,
			label: body.label,
			version: 1,
			fields: body.fields ?? [],
			flowConfig: body.flowConfig,
			createdAt: now,
			updatedAt: now,
		};
		resourceTypes = [created, ...resourceTypes];
		return HttpResponse.json(created, { status: 201 });
	}),

	http.get('*/resource-types/:resourceTypeId', async ({ params }) => {
		await delay(300);
		const found = resourceTypes.find((type) => type.id === params.resourceTypeId);
		return found ? HttpResponse.json(found) : notFound('No resource type with that id.');
	}),

	http.get('*/resources', async ({ request }) => {
		await delay(300);
		const url = new URL(request.url);
		const resourceTypeId = url.searchParams.get('resourceTypeId');
		const siteId = url.searchParams.get('siteId');

		const filtered = resources.filter(
			(resource) =>
				(!resourceTypeId || resource.resourceTypeId === resourceTypeId) &&
				(!siteId || resource.siteId === siteId),
		);
		return HttpResponse.json({ data: filtered, nextCursor: null });
	}),

	http.post('*/resources', async ({ request }) => {
		const body = (await request.json()) as CreateResourceRequest;
		await delay(300);

		if (!resourceTypes.some((type) => type.id === body.resourceTypeId)) {
			return notFound('No resource type with that id.');
		}

		const now = new Date().toISOString();
		const created: Resource = {
			id: crypto.randomUUID(),
			resourceTypeId: body.resourceTypeId,
			siteId: body.siteId,
			label: body.label,
			customFieldValues: body.customFieldValues ?? {},
			createdAt: now,
			updatedAt: now,
		};
		resources = [created, ...resources];
		return HttpResponse.json(created, { status: 201 });
	}),

	http.get('*/resources/:resourceId', async ({ params }) => {
		await delay(300);
		const found = resources.find((resource) => resource.id === params.resourceId);
		return found ? HttpResponse.json(found) : notFound('No resource with that id.');
	}),
];
