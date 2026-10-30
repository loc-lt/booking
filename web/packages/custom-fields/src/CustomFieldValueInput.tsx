import type { FieldDefinition } from '@booking-core/api-client';
import {
	Checkbox,
	Input,
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@booking-core/ui';

export interface ReferenceOption {
	value: string;
	label: string;
}

export interface CustomFieldValueInputProps {
	field: FieldDefinition;
	value: unknown;
	onChange: (value: unknown) => void;
	id: string;
	/** Candidate resources for `reference` fields, keyed by target resource type id. */
	referenceOptions?: Record<string, ReferenceOption[]>;
}

/**
 * Renders the right input for one custom field's value, given its
 * definition. This is a plain-input v1: it doesn't yet validate against the
 * field's compiled JSON Schema the way docs/frontend.md's Ajv step will —
 * see FieldDefinitionsEditor for where that validation belongs next.
 */
export function CustomFieldValueInput({
	field,
	value,
	onChange,
	id,
	referenceOptions,
}: CustomFieldValueInputProps) {
	switch (field.type) {
		case 'boolean':
			return (
				<Checkbox
					id={id}
					checked={Boolean(value)}
					onCheckedChange={(checked) => onChange(checked)}
				/>
			);

		case 'integer':
		case 'number':
			return (
				<Input
					id={id}
					type='number'
					value={typeof value === 'number' ? value : ''}
					onChange={(e) => onChange(e.target.value === '' ? undefined : Number(e.target.value))}
				/>
			);

		case 'date':
			return (
				<Input
					id={id}
					type='date'
					value={typeof value === 'string' ? value : ''}
					onChange={(e) => onChange(e.target.value || undefined)}
				/>
			);

		case 'datetime':
			return (
				<Input
					id={id}
					type='datetime-local'
					value={typeof value === 'string' ? value : ''}
					onChange={(e) => onChange(e.target.value || undefined)}
				/>
			);

		case 'select':
			return (
				<Select
					items={field.options ?? []}
					value={typeof value === 'string' ? value : ''}
					onValueChange={(next) => onChange(next ?? undefined)}
				>
					<SelectTrigger id={id} className='w-full'>
						<SelectValue placeholder='Select…' />
					</SelectTrigger>
					<SelectContent>
						{(field.options ?? []).map((option) => (
							<SelectItem key={option.value} value={option.value}>
								{option.label}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
			);

		case 'email':
		case 'url':
		case 'phone':
		case 'text':
		case 'long_text':
			return (
				<Input
					id={id}
					value={typeof value === 'string' ? value : ''}
					onChange={(e) => onChange(e.target.value || undefined)}
				/>
			);

		case 'reference': {
			const targetId = field.validation?.targetResourceTypeId;
			const options = (targetId ? referenceOptions?.[targetId] : undefined) ?? [];
			return (
				<Select
					items={options}
					value={typeof value === 'string' ? value : ''}
					onValueChange={(next) => onChange(next ?? undefined)}
				>
					<SelectTrigger id={id} className='w-full'>
						<SelectValue placeholder={options.length ? 'Select…' : 'No resources available'} />
					</SelectTrigger>
					<SelectContent>
						{options.map((option) => (
							<SelectItem key={option.value} value={option.value}>
								{option.label}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
			);
		}

		default:
			// multi_select, file, multi_file: no dedicated input yet.
			return (
				<Input
					id={id}
					value={typeof value === 'string' ? value : ''}
					onChange={(e) => onChange(e.target.value || undefined)}
					placeholder={`${field.type} — enter raw value`}
				/>
			);
	}
}
