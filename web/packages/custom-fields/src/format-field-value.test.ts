import type { FieldDefinition } from '@booking-core/api-client';
import { describe, expect, it } from 'vitest';
import { formatFieldValue } from './format-field-value';

function field(overrides: Partial<FieldDefinition>): FieldDefinition {
	return { key: 'field', label: 'Field', type: 'text', ...overrides };
}

describe('formatFieldValue', () => {
	it('shows an em dash for null, undefined and empty values', () => {
		const textField = field({ type: 'text' });
		expect(formatFieldValue(textField, null)).toBe('—');
		expect(formatFieldValue(textField, undefined)).toBe('—');
		expect(formatFieldValue(textField, '')).toBe('—');
	});

	it('formats booleans as Yes/No', () => {
		const booleanField = field({ type: 'boolean' });
		expect(formatFieldValue(booleanField, true)).toBe('Yes');
		expect(formatFieldValue(booleanField, false)).toBe('No');
	});

	it('looks up the option label for select, not the raw stored value', () => {
		const selectField = field({
			type: 'select',
			options: [{ value: 'has_desk', label: 'Has a desk' }],
		});
		expect(formatFieldValue(selectField, 'has_desk')).toBe('Has a desk');
	});

	it('falls back to the raw value when a select option is unknown', () => {
		const selectField = field({ type: 'select', options: [] });
		expect(formatFieldValue(selectField, 'mystery')).toBe('mystery');
	});

	it('joins multi_select option labels with a comma', () => {
		const multiSelectField = field({
			type: 'multi_select',
			options: [
				{ value: 'a', label: 'Option A' },
				{ value: 'b', label: 'Option B' },
			],
		});
		expect(formatFieldValue(multiSelectField, ['a', 'b'])).toBe('Option A, Option B');
	});

	it('counts multi_file values instead of listing them', () => {
		const multiFileField = field({ type: 'multi_file' });
		expect(formatFieldValue(multiFileField, ['a.pdf', 'b.pdf'])).toBe('2 file(s)');
	});

	it('falls back to the raw string for an unparsable date', () => {
		const dateField = field({ type: 'date' });
		expect(formatFieldValue(dateField, 'not-a-date')).toBe('not-a-date');
	});

	it('resolves a reference value to the matching resource label', () => {
		const referenceField = field({
			type: 'reference',
			validation: { targetResourceTypeId: 'table-type' },
		});
		const referenceOptions = { 'table-type': [{ value: 'table-a', label: 'Table A' }] };
		expect(formatFieldValue(referenceField, 'table-a', referenceOptions)).toBe('Table A');
	});

	it('falls back to the raw id when a reference value has no matching resource', () => {
		const referenceField = field({
			type: 'reference',
			validation: { targetResourceTypeId: 'table-type' },
		});
		expect(formatFieldValue(referenceField, 'table-a', {})).toBe('table-a');
	});
});
