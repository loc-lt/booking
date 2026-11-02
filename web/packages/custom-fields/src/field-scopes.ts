import type { FieldDefinition, FieldScope } from '@booking-core/api-client';

export interface FieldScopeOption {
	value: FieldScope;
	label: string;
}

/** `scope` defaults to `resource` per the contract (FieldDefinition.scope). */
export const DEFAULT_FIELD_SCOPE: FieldScope = 'resource';

export const FIELD_SCOPE_OPTIONS: FieldScopeOption[] = [
	{ value: 'resource', label: 'Set on the resource' },
	{ value: 'booking', label: 'Collected at booking' },
];

export const FIELD_SCOPE_LABELS: Record<FieldScope, string> = Object.fromEntries(
	FIELD_SCOPE_OPTIONS.map((option) => [option.value, option.label]),
) as Record<FieldScope, string>;

export function fieldScope(field: FieldDefinition): FieldScope {
	return field.scope ?? DEFAULT_FIELD_SCOPE;
}

/** Fields an admin sets once per resource instance, e.g. a meeting room's TV type. */
export function isResourceScoped(field: FieldDefinition): boolean {
	return fieldScope(field) === 'resource';
}

/** Fields collected from the member on every booking, e.g. number of attendees. */
export function isBookingScoped(field: FieldDefinition): boolean {
	return fieldScope(field) === 'booking';
}
