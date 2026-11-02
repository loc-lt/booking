import type { FieldDefinition } from '@booking-core/api-client';
import { Label } from '@booking-core/ui';
import { CustomFieldValueInput, type ReferenceOption } from './custom-field-value-input';

export interface CustomFieldValuesEditorProps {
	fields: FieldDefinition[];
	values: Record<string, unknown>;
	onChange: (next: Record<string, unknown>) => void;
	/** Field key -> error message, e.g. from a VALIDATION_FAILED response. */
	errors?: Record<string, string>;
	/** Candidate resources for `reference` fields, keyed by target resource type id. */
	referenceOptions?: Record<string, ReferenceOption[]>;
}

/** Renders one input per custom field, for filling in a resource's field values. */
export function CustomFieldValuesEditor({
	fields,
	values,
	onChange,
	errors,
	referenceOptions,
}: CustomFieldValuesEditorProps) {
	function setValue(key: string, value: unknown) {
		onChange({ ...values, [key]: value });
	}

	return (
		<div className='flex flex-col gap-3'>
			{fields.map((field) => {
				const id = `field-value-${field.key}`;
				if (field.type === 'boolean') {
					return (
						<div key={field.key} className='flex items-center gap-2'>
							<CustomFieldValueInput
								id={id}
								field={field}
								value={values[field.key]}
								onChange={(value) => setValue(field.key, value)}
								referenceOptions={referenceOptions}
							/>
							<Label htmlFor={id}>
								{field.label}
								{field.required ? ' *' : ''}
							</Label>
						</div>
					);
				}

				return (
					<div key={field.key} className='space-y-1'>
						<Label htmlFor={id}>
							{field.label}
							{field.required ? ' *' : ''}
						</Label>
						<CustomFieldValueInput
							id={id}
							field={field}
							value={values[field.key]}
							onChange={(value) => setValue(field.key, value)}
							referenceOptions={referenceOptions}
						/>
						{field.help && <p className='text-muted-foreground text-xs'>{field.help}</p>}
						{errors?.[field.key] && <p className='text-destructive text-sm'>{errors[field.key]}</p>}
					</div>
				);
			})}
		</div>
	);
}
