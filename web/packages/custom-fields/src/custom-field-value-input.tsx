import type { FieldDefinition } from '@booking-core/api-client';
import {
	Checkbox,
	ClearableInput,
	DatePicker,
	DateTimePicker,
	formatCalendarDate,
	Input,
	padNumber,
	parseCalendarDateTime,
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

/** `datetime` fields store a full ISO string (docs/domain/configuration.md); `DateTimePicker` works in `"YYYY-MM-DD HH:MM:SS"`. */
function isoToDateTimePickerValue(value: string): string {
	const date = new Date(value);

	if (Number.isNaN(date.getTime())) {
		return '';
	}

	const time = [date.getHours(), date.getMinutes(), date.getSeconds()].map(padNumber).join(':');
	return `${formatCalendarDate(date)} ${time}`;
}

function dateTimePickerValueToIso(value: string): string | undefined {
	return parseCalendarDateTime(value)?.toISOString();
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
				<DatePicker
					id={id}
					clearLabel='Clear'
					onValueChange={(next) => onChange(next || undefined)}
					placeholder='Pick a date'
					submitLabel='Apply'
					value={typeof value === 'string' ? value : ''}
				/>
			);

		case 'datetime':
			return (
				<DateTimePicker
					id={id}
					clearLabel='Clear'
					onValueChange={(next) => onChange(next ? dateTimePickerValueToIso(next) : undefined)}
					placeholder='Pick a date and time'
					submitLabel='Apply'
					value={typeof value === 'string' ? isoToDateTimePickerValue(value) : ''}
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
				<ClearableInput
					id={id}
					clearLabel='Clear'
					onChange={(e) => onChange(e.target.value || undefined)}
					onClear={() => onChange(undefined)}
					value={typeof value === 'string' ? value : ''}
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
				<ClearableInput
					id={id}
					clearLabel='Clear'
					onChange={(e) => onChange(e.target.value || undefined)}
					onClear={() => onChange(undefined)}
					placeholder={`${field.type} — enter raw value`}
					value={typeof value === 'string' ? value : ''}
				/>
			);
	}
}
