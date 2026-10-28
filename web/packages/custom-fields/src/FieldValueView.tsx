import type { FieldDefinition } from '@booking-core/api-client';
import { formatFieldValue } from './formatFieldValue';

export interface FieldValueViewProps {
	field: FieldDefinition;
	value: unknown;
}

/** Renders one custom field's value for display, e.g. in a resource list or detail page. */
export function FieldValueView({ field, value }: FieldValueViewProps) {
	return (
		<div className='flex items-baseline gap-1 text-sm'>
			<span className='text-muted-foreground'>{field.label}:</span>
			<span>{formatFieldValue(field, value)}</span>
		</div>
	);
}
