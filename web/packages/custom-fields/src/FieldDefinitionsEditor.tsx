import type { FieldDefinition, FieldOption, FieldScope, FieldType } from '@booking-core/api-client';
import {
	Button,
	Checkbox,
	Input,
	Label,
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@booking-core/ui';
import { FieldValidationFields } from './FieldValidationFields';
import { DEFAULT_FIELD_SCOPE, FIELD_SCOPE_OPTIONS, fieldScope } from './fieldScopes';
import { FIELD_TYPE_OPTIONS, fieldTypeNeedsOptions, fieldTypeValidationKind } from './fieldTypes';

export interface ResourceTypeOption {
	value: string;
	label: string;
}

export interface FieldDefinitionsEditorProps {
	value: FieldDefinition[];
	onChange: (next: FieldDefinition[]) => void;
	/** Per-field error message, keyed by the field's position in `value`. */
	errors?: Record<number, string>;
	/** Resource types a `reference` field can target. */
	resourceTypeOptions?: ResourceTypeOption[];
}

function emptyField(): FieldDefinition {
	return { key: '', label: '', type: 'text', scope: DEFAULT_FIELD_SCOPE, required: false };
}

/**
 * Lets an admin author a resource type's custom field definitions: key,
 * label, type, required, and the option list for select/multi_select.
 * Controlled, framework-agnostic — the console wires it into its form.
 */
export function FieldDefinitionsEditor({
	value,
	onChange,
	errors,
	resourceTypeOptions = [],
}: FieldDefinitionsEditorProps) {
	function updateField(index: number, patch: Partial<FieldDefinition>) {
		onChange(value.map((field, i) => (i === index ? { ...field, ...patch } : field)));
	}

	function removeField(index: number) {
		onChange(value.filter((_, i) => i !== index));
	}

	function changeFieldType(index: number, type: FieldType) {
		// Clear options/validation that no longer apply to the new type, so a
		// stale pattern or option list doesn't ride along silently.
		onChange(
			value.map((field, i) => {
				if (i !== index) return field;
				const kindChanged = fieldTypeValidationKind(field.type) !== fieldTypeValidationKind(type);
				return {
					...field,
					type,
					options: fieldTypeNeedsOptions(type) ? field.options : undefined,
					validation: kindChanged ? undefined : field.validation,
				};
			}),
		);
	}

	function addField() {
		onChange([...value, emptyField()]);
	}

	return (
		<div className='flex flex-col gap-3'>
			{value.length === 0 && <p className='text-muted-foreground text-sm'>No custom fields yet.</p>}
			{value.map((field, index) => (
				<div
					// biome-ignore lint/suspicious/noArrayIndexKey: fields have no stable id while being edited
					key={index}
					className='flex flex-col gap-2 rounded-lg border p-3'
				>
					<div className='flex items-start gap-2'>
						<div className='flex-1 space-y-1'>
							<Label htmlFor={`field-${index}-label`}>Label</Label>
							<Input
								id={`field-${index}-label`}
								value={field.label}
								onChange={(e) => updateField(index, { label: e.target.value })}
								placeholder='Floor'
							/>
						</div>
						<div className='flex-1 space-y-1'>
							<Label htmlFor={`field-${index}-key`}>Key</Label>
							<Input
								id={`field-${index}-key`}
								value={field.key}
								onChange={(e) => updateField(index, { key: e.target.value })}
								placeholder='floor'
								aria-invalid={errors?.[index] ? true : undefined}
							/>
						</div>
						<div className='w-40 space-y-1'>
							<Label htmlFor={`field-${index}-type`}>Type</Label>
							<Select
								items={FIELD_TYPE_OPTIONS}
								value={field.type}
								onValueChange={(next) => changeFieldType(index, next as FieldType)}
							>
								<SelectTrigger id={`field-${index}-type`}>
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									{FIELD_TYPE_OPTIONS.map((option) => (
										<SelectItem key={option.value} value={option.value}>
											{option.label}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>
						<div className='w-48 space-y-1'>
							<Label htmlFor={`field-${index}-scope`}>Collected from</Label>
							<Select
								items={FIELD_SCOPE_OPTIONS}
								value={fieldScope(field)}
								onValueChange={(next) => updateField(index, { scope: next as FieldScope })}
							>
								<SelectTrigger id={`field-${index}-scope`}>
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									{FIELD_SCOPE_OPTIONS.map((option) => (
										<SelectItem key={option.value} value={option.value}>
											{option.label}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>
						<Button type='button' variant='ghost' onClick={() => removeField(index)}>
							Remove
						</Button>
					</div>

					<div className='flex items-center gap-2 text-sm'>
						<Checkbox
							id={`field-${index}-required`}
							checked={field.required ?? false}
							onCheckedChange={(checked) => updateField(index, { required: checked })}
						/>
						<Label htmlFor={`field-${index}-required`}>Required</Label>
					</div>

					{fieldTypeNeedsOptions(field.type) && (
						<FieldOptionsEditor
							options={field.options ?? []}
							onChange={(options) => updateField(index, { options })}
						/>
					)}

					{field.type === 'reference' && (
						<ReferenceTargetEditor
							idPrefix={`field-${index}-target`}
							resourceTypeOptions={resourceTypeOptions}
							value={field.validation?.targetResourceTypeId}
							onChange={(targetResourceTypeId) =>
								updateField(index, { validation: { ...field.validation, targetResourceTypeId } })
							}
						/>
					)}

					<FieldValidationFields
						idPrefix={`field-${index}-validation`}
						type={field.type}
						value={field.validation}
						onChange={(validation) => updateField(index, { validation })}
					/>

					{errors?.[index] && <p className='text-destructive text-sm'>{errors[index]}</p>}
				</div>
			))}

			<Button type='button' variant='outline' onClick={addField}>
				Add custom field
			</Button>
		</div>
	);
}

function ReferenceTargetEditor({
	idPrefix,
	resourceTypeOptions,
	value,
	onChange,
}: {
	idPrefix: string;
	resourceTypeOptions: ResourceTypeOption[];
	value: string | undefined;
	onChange: (next: string | undefined) => void;
}) {
	if (resourceTypeOptions.length === 0) {
		return (
			<p className='text-muted-foreground text-sm'>
				Create another resource type first — a reference field needs one to point at.
			</p>
		);
	}

	return (
		<div className='w-64 space-y-1'>
			<Label htmlFor={idPrefix}>References</Label>
			<Select
				items={resourceTypeOptions}
				value={value ?? ''}
				onValueChange={(next) => onChange(next ?? undefined)}
			>
				<SelectTrigger id={idPrefix}>
					<SelectValue placeholder='Choose a resource type…' />
				</SelectTrigger>
				<SelectContent>
					{resourceTypeOptions.map((option) => (
						<SelectItem key={option.value} value={option.value}>
							{option.label}
						</SelectItem>
					))}
				</SelectContent>
			</Select>
		</div>
	);
}

function FieldOptionsEditor({
	options,
	onChange,
}: {
	options: FieldOption[];
	onChange: (next: FieldOption[]) => void;
}) {
	function updateOption(index: number, patch: Partial<FieldOption>) {
		onChange(options.map((option, i) => (i === index ? { ...option, ...patch } : option)));
	}

	function removeOption(index: number) {
		onChange(options.filter((_, i) => i !== index));
	}

	function addOption() {
		onChange([...options, { value: '', label: '' }]);
	}

	return (
		<div className='flex flex-col gap-2 pl-4'>
			<Label>Options</Label>
			{options.map((option, index) => (
				<div
					// biome-ignore lint/suspicious/noArrayIndexKey: options have no stable id while being edited
					key={index}
					className='flex items-center gap-2'
				>
					<Input
						value={option.label}
						onChange={(e) => updateOption(index, { label: e.target.value })}
						placeholder='Label'
					/>
					<Input
						value={option.value}
						onChange={(e) => updateOption(index, { value: e.target.value })}
						placeholder='value'
					/>
					<Button type='button' variant='ghost' size='sm' onClick={() => removeOption(index)}>
						Remove
					</Button>
				</div>
			))}
			<Button type='button' variant='outline' size='sm' onClick={addOption}>
				Add option
			</Button>
		</div>
	);
}
