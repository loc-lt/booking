import type { FieldType, FieldValidation } from '@booking-core/api-client';
import { ClearableInput, Input, Label } from '@booking-core/ui';
import { fieldTypeValidationKind } from './field-types';

export interface FieldValidationFieldsProps {
	idPrefix: string;
	type: FieldType;
	value: FieldValidation | undefined;
	onChange: (next: FieldValidation | undefined) => void;
}

function setProp(
	value: FieldValidation | undefined,
	key: keyof FieldValidation,
	next: number | string | undefined,
): FieldValidation | undefined {
	const updated: FieldValidation = { ...value };
	if (next === undefined || next === '') {
		delete updated[key];
	} else {
		// biome-ignore lint/suspicious/noExplicitAny: FieldValidation's keys are a mix of string and number types
		(updated as any)[key] = next;
	}
	return Object.keys(updated).length > 0 ? updated : undefined;
}

function numberInput(
	id: string,
	label: string,
	key: 'minLength' | 'maxLength' | 'min' | 'max' | 'multipleOf' | 'minItems' | 'maxItems',
	value: FieldValidation | undefined,
	onChange: (next: FieldValidation | undefined) => void,
) {
	return (
		<div className='space-y-1' key={key}>
			<Label htmlFor={id}>{label}</Label>
			<Input
				id={id}
				type='number'
				value={value?.[key] ?? ''}
				onChange={(e) =>
					onChange(setProp(value, key, e.target.value === '' ? undefined : Number(e.target.value)))
				}
			/>
		</div>
	);
}

/** Shows the validation inputs relevant to a field's type — see docs/domain/configuration.md. */
export function FieldValidationFields({
	idPrefix,
	type,
	value,
	onChange,
}: FieldValidationFieldsProps) {
	const kind = fieldTypeValidationKind(type);

	if (kind === 'text') {
		return (
			<div className='grid grid-cols-3 gap-2'>
				{numberInput(`${idPrefix}-min-length`, 'Min length', 'minLength', value, onChange)}
				{numberInput(`${idPrefix}-max-length`, 'Max length', 'maxLength', value, onChange)}
				<div className='space-y-1'>
					<Label htmlFor={`${idPrefix}-pattern`}>Pattern</Label>
					<ClearableInput
						id={`${idPrefix}-pattern`}
						clearLabel='Clear'
						onChange={(e) => onChange(setProp(value, 'pattern', e.target.value))}
						onClear={() => onChange(setProp(value, 'pattern', undefined))}
						placeholder='^[A-Z]{2}\d{4}$'
						value={value?.pattern ?? ''}
					/>
				</div>
			</div>
		);
	}

	if (kind === 'numeric') {
		return (
			<div className='grid grid-cols-3 gap-2'>
				{numberInput(`${idPrefix}-min`, 'Min', 'min', value, onChange)}
				{numberInput(`${idPrefix}-max`, 'Max', 'max', value, onChange)}
				{numberInput(`${idPrefix}-multiple-of`, 'Multiple of', 'multipleOf', value, onChange)}
			</div>
		);
	}

	if (kind === 'array') {
		return (
			<div className='grid grid-cols-2 gap-2'>
				{numberInput(`${idPrefix}-min-items`, 'Min items', 'minItems', value, onChange)}
				{numberInput(`${idPrefix}-max-items`, 'Max items', 'maxItems', value, onChange)}
			</div>
		);
	}

	return null;
}
