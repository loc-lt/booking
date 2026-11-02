import type { FieldType } from '@booking-core/api-client';

export interface FieldTypeOption {
	value: FieldType;
	label: string;
}

/** Human labels for FieldType, see docs/domain/configuration.md's field types table. */
export const FIELD_TYPE_OPTIONS: FieldTypeOption[] = [
	{ value: 'text', label: 'Text' },
	{ value: 'long_text', label: 'Long text' },
	{ value: 'integer', label: 'Integer' },
	{ value: 'number', label: 'Number' },
	{ value: 'boolean', label: 'Yes / no' },
	{ value: 'date', label: 'Date' },
	{ value: 'datetime', label: 'Date & time' },
	{ value: 'select', label: 'Select' },
	{ value: 'multi_select', label: 'Multi-select' },
	{ value: 'email', label: 'Email' },
	{ value: 'url', label: 'URL' },
	{ value: 'phone', label: 'Phone' },
	{ value: 'reference', label: 'Reference' },
	{ value: 'file', label: 'File' },
	{ value: 'multi_file', label: 'Multiple files' },
];

export const FIELD_TYPE_LABELS: Record<FieldType, string> = Object.fromEntries(
	FIELD_TYPE_OPTIONS.map((option) => [option.value, option.label]),
) as Record<FieldType, string>;

/** select and multi_select need an option list; see FieldDefinition.options in the contract. */
export function fieldTypeNeedsOptions(type: FieldType): boolean {
	return type === 'select' || type === 'multi_select';
}

export type FieldValidationKind = 'text' | 'numeric' | 'array' | 'reference' | 'none';

const TEXT_TYPES: FieldType[] = ['text', 'long_text', 'email', 'url', 'phone'];
const NUMERIC_TYPES: FieldType[] = ['integer', 'number'];

/** Which validation inputs a field type takes, per docs/domain/configuration.md's field types table. */
export function fieldTypeValidationKind(type: FieldType): FieldValidationKind {
	if (TEXT_TYPES.includes(type)) return 'text';
	if (NUMERIC_TYPES.includes(type)) return 'numeric';
	if (type === 'multi_select') return 'array';
	if (type === 'reference') return 'reference';
	return 'none';
}
