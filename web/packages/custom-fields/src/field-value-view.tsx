import type { FieldDefinition } from '@booking-core/api-client';
import type { ReferenceOption } from './custom-field-value-input';
import { formatFieldValue } from './format-field-value';

export interface FieldValueViewProps {
	field: FieldDefinition;
	value: unknown;
	/** Candidate resources for `reference` fields, keyed by target resource type id. */
	referenceOptions?: Record<string, ReferenceOption[]>;
}

/** Renders one custom field's value for display, e.g. in a resource list or detail page. */
export function FieldValueView({ field, value, referenceOptions }: FieldValueViewProps) {
	return (
		<div className='flex items-baseline gap-1 text-sm'>
			<span className='text-muted-foreground'>{field.label}:</span>
			<span>{formatFieldValue(field, value, referenceOptions)}</span>
		</div>
	);
}
