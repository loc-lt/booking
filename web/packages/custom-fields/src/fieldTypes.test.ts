import type { FieldType } from '@booking-core/api-client';
import { describe, expect, it } from 'vitest';
import { fieldTypeNeedsOptions, fieldTypeValidationKind } from './fieldTypes';

describe('fieldTypeNeedsOptions', () => {
	it('is true only for select and multi_select', () => {
		expect(fieldTypeNeedsOptions('select')).toBe(true);
		expect(fieldTypeNeedsOptions('multi_select')).toBe(true);
	});

	it('is false for every other field type', () => {
		const others: FieldType[] = [
			'text',
			'long_text',
			'integer',
			'number',
			'boolean',
			'date',
			'datetime',
			'email',
			'url',
			'phone',
			'reference',
			'file',
			'multi_file',
		];
		for (const type of others) {
			expect(fieldTypeNeedsOptions(type)).toBe(false);
		}
	});
});

describe('fieldTypeValidationKind', () => {
	it('is "text" for the string-ish types', () => {
		for (const type of ['text', 'long_text', 'email', 'url', 'phone'] as const) {
			expect(fieldTypeValidationKind(type)).toBe('text');
		}
	});

	it('is "numeric" for integer and number', () => {
		expect(fieldTypeValidationKind('integer')).toBe('numeric');
		expect(fieldTypeValidationKind('number')).toBe('numeric');
	});

	it('is "array" for multi_select', () => {
		expect(fieldTypeValidationKind('multi_select')).toBe('array');
	});

	it('is "none" for date and datetime — the contract has no date bounds yet', () => {
		expect(fieldTypeValidationKind('date')).toBe('none');
		expect(fieldTypeValidationKind('datetime')).toBe('none');
	});

	it('is "none" for boolean, select, file and multi_file', () => {
		for (const type of ['boolean', 'select', 'file', 'multi_file'] as const) {
			expect(fieldTypeValidationKind(type)).toBe('none');
		}
	});

	it('is "reference" for reference fields, so switching away clears the target type', () => {
		expect(fieldTypeValidationKind('reference')).toBe('reference');
	});
});
