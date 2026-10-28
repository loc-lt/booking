import type { FieldDefinition } from '@booking-core/api-client';

/** Formats a custom field's stored value for display, given its definition. */
export function formatFieldValue(field: FieldDefinition, value: unknown): string {
	if (value === null || value === undefined || value === '') {
		return '—';
	}

	switch (field.type) {
		case 'boolean':
			return value ? 'Yes' : 'No';
		case 'select':
			return optionLabel(field, String(value));
		case 'multi_select':
			return Array.isArray(value)
				? value.map((item) => optionLabel(field, String(item))).join(', ')
				: String(value);
		case 'multi_file':
			return Array.isArray(value) ? `${value.length} file(s)` : String(value);
		case 'date':
		case 'datetime':
			return formatDate(String(value), field.type);
		default:
			return String(value);
	}
}

function optionLabel(field: FieldDefinition, value: string): string {
	return field.options?.find((option) => option.value === value)?.label ?? value;
}

function formatDate(value: string, type: 'date' | 'datetime'): string {
	const parsed = new Date(value);
	if (Number.isNaN(parsed.getTime())) {
		return value;
	}
	return type === 'date' ? parsed.toLocaleDateString() : parsed.toLocaleString();
}
