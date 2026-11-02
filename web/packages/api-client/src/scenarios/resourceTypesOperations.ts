import type {
	CreateResourceRequest,
	CreateResourceTypeRequest,
	FieldError,
	Resource,
	ResourceType,
	UpdateResourceTypeRequest,
} from '../generated/models';

/**
 * Transport-agnostic resource type/resource operations: the same demo "backend"
 * logic used by the in-browser MSW scenario (resourceTypesStore.ts, for solo
 * dev and tests) and by the shared mock server (mock-server/, so console and
 * member see each other's data). Kept framework-free so both can call it.
 */

export interface OperationResult<T> {
	status: number;
	body: T;
}

const DEMO_SITE_ID = '0193f4c2-8b4c-7d4f-9f3b-2a0c7d6e5f4b';
const PHONE_BOOTH_TYPE_ID = '0193f4c2-7a3b-7c3e-8e2a-1f9b6c5d4e3a';
const TABLE_TYPE_ID = '0193f4c2-7a3b-7c3e-8e2a-2f0c7d6e5f4b';
const CONFERENCE_ROOM_TYPE_ID = '0193f4c2-7a3b-7c3e-8e2a-3f1c7d6e5f4b';
const TABLE_A_ID = '0193f4c3-2c3d-7b4e-af5d-6d4f1a0b9c8e';
const TABLE_B_ID = '0193f4c3-3d4e-7c5f-8a6e-7e5a2b1c0d9f';

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
					scope: 'resource',
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
		{
			id: TABLE_TYPE_ID,
			key: 'table',
			label: 'Table',
			version: 1,
			fields: [],
			flowConfig: {
				confirmation: 'instant',
				checkIn: { required: false, opensMinutesBefore: 0, noShowAfterMinutes: 0 },
				cancellation: { allowedUntilMinutesBefore: 0 },
			},
			createdAt: '2026-10-30T09:00:00+07:00',
			updatedAt: '2026-10-30T09:00:00+07:00',
		},
		{
			id: CONFERENCE_ROOM_TYPE_ID,
			key: 'conference_room',
			label: 'Conference room',
			version: 1,
			fields: [
				{
					key: 'primary_table',
					label: 'Primary table',
					type: 'reference',
					scope: 'resource',
					validation: { targetResourceTypeId: TABLE_TYPE_ID },
				},
			],
			flowConfig: {
				confirmation: 'instant',
				checkIn: { required: true, opensMinutesBefore: 15, noShowAfterMinutes: 15 },
				cancellation: { allowedUntilMinutesBefore: 60 },
			},
			createdAt: '2026-10-30T09:00:00+07:00',
			updatedAt: '2026-10-30T09:00:00+07:00',
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
		{
			id: TABLE_A_ID,
			resourceTypeId: TABLE_TYPE_ID,
			siteId: DEMO_SITE_ID,
			label: 'Table A',
			customFieldValues: {},
			createdAt: '2026-10-30T09:05:00+07:00',
			updatedAt: '2026-10-30T09:05:00+07:00',
		},
		{
			id: TABLE_B_ID,
			resourceTypeId: TABLE_TYPE_ID,
			siteId: DEMO_SITE_ID,
			label: 'Table B',
			customFieldValues: {},
			createdAt: '2026-10-30T09:05:00+07:00',
			updatedAt: '2026-10-30T09:05:00+07:00',
		},
		{
			id: '0193f4c3-4e5f-7d6a-9b7f-8f6b3c2d1e0a',
			resourceTypeId: CONFERENCE_ROOM_TYPE_ID,
			siteId: DEMO_SITE_ID,
			label: 'Conference Room 1',
			customFieldValues: { primary_table: TABLE_A_ID },
			createdAt: '2026-10-30T09:10:00+07:00',
			updatedAt: '2026-10-30T09:10:00+07:00',
		},
		{
			id: '0193f4c3-5f6a-7e7b-ac8a-9a7c4d3e2f1b',
			resourceTypeId: CONFERENCE_ROOM_TYPE_ID,
			siteId: DEMO_SITE_ID,
			label: 'Conference Room 2',
			customFieldValues: { primary_table: TABLE_B_ID },
			createdAt: '2026-10-30T09:10:00+07:00',
			updatedAt: '2026-10-30T09:10:00+07:00',
		},
	];
}

let resourceTypes = seedResourceTypes();
let resources = seedResources();

/** Restores the seeded resource types and resources. Call between tests. */
export function resetResourceTypesState(): void {
	resourceTypes = seedResourceTypes();
	resources = seedResources();
}

function validationFailed(errors: FieldError[]): OperationResult<unknown> {
	return {
		status: 422,
		body: {
			type: 'about:blank',
			title: 'Validation failed',
			status: 422,
			code: 'VALIDATION_FAILED',
			errors,
		},
	};
}

function notFound(detail: string): OperationResult<unknown> {
	return {
		status: 404,
		body: { type: 'about:blank', title: 'Not found', status: 404, code: 'NOT_FOUND', detail },
	};
}

function staleVersion(detail: string): OperationResult<unknown> {
	return {
		status: 409,
		body: {
			type: 'about:blank',
			title: 'Stale version',
			status: 409,
			code: 'STALE_VERSION',
			detail,
		},
	};
}

export function listResourceTypesOp(): OperationResult<{ data: ResourceType[]; nextCursor: null }> {
	return { status: 200, body: { data: resourceTypes, nextCursor: null } };
}

export function createResourceTypeOp(body: CreateResourceTypeRequest): OperationResult<unknown> {
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
	return { status: 201, body: created };
}

export function getResourceTypeOp(resourceTypeId: string): OperationResult<unknown> {
	const found = resourceTypes.find((type) => type.id === resourceTypeId);
	return found ? { status: 200, body: found } : notFound('No resource type with that id.');
}

export function updateResourceTypeOp(
	resourceTypeId: string,
	body: UpdateResourceTypeRequest,
): OperationResult<unknown> {
	const found = resourceTypes.find((type) => type.id === resourceTypeId);
	if (!found) return notFound('No resource type with that id.');
	if (found.version !== body.baseVersion) {
		return staleVersion('Someone else changed this resource type since you loaded it.');
	}

	const now = new Date().toISOString();
	const updated: ResourceType = {
		...found,
		version: found.version + 1,
		flowConfig: body.flowConfig,
		updatedAt: now,
	};
	resourceTypes = resourceTypes.map((type) => (type.id === updated.id ? updated : type));
	return { status: 200, body: updated };
}

export function listResourcesOp(query: {
	resourceTypeId?: string | null;
	siteId?: string | null;
}): OperationResult<{ data: Resource[]; nextCursor: null }> {
	const filtered = resources.filter(
		(resource) =>
			(!query.resourceTypeId || resource.resourceTypeId === query.resourceTypeId) &&
			(!query.siteId || resource.siteId === query.siteId),
	);
	return { status: 200, body: { data: filtered, nextCursor: null } };
}

export function createResourceOp(body: CreateResourceRequest): OperationResult<unknown> {
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
	return { status: 201, body: created };
}

export function getResourceOp(resourceId: string): OperationResult<unknown> {
	const found = resources.find((resource) => resource.id === resourceId);
	return found ? { status: 200, body: found } : notFound('No resource with that id.');
}

/** Plain lookup (not wrapped in an OperationResult) for other operations that need a resource's own type/site, e.g. when creating a booking. */
export function findResource(resourceId: string): Resource | undefined {
	return resources.find((resource) => resource.id === resourceId);
}

/** Plain lookup (not wrapped in an OperationResult) for other operations that need a resource type's live flow config, e.g. when creating a booking. */
export function findResourceType(resourceTypeId: string): ResourceType | undefined {
	return resourceTypes.find((type) => type.id === resourceTypeId);
}
