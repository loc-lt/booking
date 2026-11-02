import type { FieldDefinition } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { CustomFieldValueInput } from './custom-field-value-input';

const TEXT_FIELD: FieldDefinition = { key: 'floor', label: 'Floor', type: 'text' };

const meta = {
	title: 'custom-fields/CustomFieldValueInput',
	component: CustomFieldValueInput,
	tags: ['autodocs'],
	args: {
		id: 'custom-field-value-story',
		// Overridden by `CustomFieldValueInputDemo`'s own state below (and by
		// each story's `field`) — required here only so every story satisfies
		// the component's required props.
		field: TEXT_FIELD,
		value: undefined,
		onChange: () => {},
	},
} satisfies Meta<typeof CustomFieldValueInput>;

export default meta;
type Story = StoryObj<typeof meta>;

function CustomFieldValueInputDemo(args: Story['args']) {
	const [value, setValue] = useState(args?.value);
	return (
		<CustomFieldValueInput
			{...args}
			field={args?.field ?? TEXT_FIELD}
			id={args?.id ?? 'custom-field-value-story'}
			value={value}
			onChange={setValue}
		/>
	);
}
export const Text: Story = {
	args: { field: TEXT_FIELD, value: '' },
	render: (args) => <CustomFieldValueInputDemo {...args} />,
};

const NUMBER_FIELD: FieldDefinition = { key: 'capacity', label: 'Capacity', type: 'number' };
export const NumberField: Story = {
	args: { field: NUMBER_FIELD, value: undefined },
	render: (args) => <CustomFieldValueInputDemo {...args} />,
};

const BOOLEAN_FIELD: FieldDefinition = {
	key: 'hasProjector',
	label: 'Has projector',
	type: 'boolean',
};
export const BooleanField: Story = {
	args: { field: BOOLEAN_FIELD, value: false },
	render: (args) => <CustomFieldValueInputDemo {...args} />,
};

const DATE_FIELD: FieldDefinition = { key: 'availableFrom', label: 'Available from', type: 'date' };
export const DateField: Story = {
	args: { field: DATE_FIELD, value: '' },
	render: (args) => <CustomFieldValueInputDemo {...args} />,
};

const DATETIME_FIELD: FieldDefinition = {
	key: 'maintenanceWindow',
	label: 'Maintenance window',
	type: 'datetime',
};
export const DateTimeField: Story = {
	args: { field: DATETIME_FIELD, value: '' },
	render: (args) => <CustomFieldValueInputDemo {...args} />,
};

const SELECT_FIELD: FieldDefinition = {
	key: 'equipment',
	label: 'Equipment',
	type: 'select',
	options: [
		{ value: 'whiteboard', label: 'Whiteboard' },
		{ value: 'tv', label: 'TV screen' },
		{ value: 'phone', label: 'Conference phone' },
	],
};
export const Select: Story = {
	args: { field: SELECT_FIELD, value: '' },
	render: (args) => <CustomFieldValueInputDemo {...args} />,
};

const REFERENCE_FIELD: FieldDefinition = {
	key: 'building',
	label: 'Building',
	type: 'reference',
	validation: { targetResourceTypeId: 'building-type' },
};
export const Reference: Story = {
	args: {
		field: REFERENCE_FIELD,
		value: '',
		referenceOptions: {
			'building-type': [
				{ value: 'north', label: 'North building' },
				{ value: 'south', label: 'South building' },
			],
		},
	},
	render: (args) => <CustomFieldValueInputDemo {...args} />,
};
