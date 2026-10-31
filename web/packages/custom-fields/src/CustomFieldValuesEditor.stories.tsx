import type { FieldDefinition } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { CustomFieldValuesEditor } from './CustomFieldValuesEditor';

const FIELDS: FieldDefinition[] = [
	{ key: 'floor', label: 'Floor', type: 'text', required: true },
	{ key: 'hasProjector', label: 'Has projector', type: 'boolean' },
	{
		key: 'equipment',
		label: 'Equipment',
		type: 'select',
		help: 'Pick the primary piece of equipment in the room.',
		options: [
			{ value: 'whiteboard', label: 'Whiteboard' },
			{ value: 'tv', label: 'TV screen' },
		],
	},
];

const meta = {
	title: 'custom-fields/CustomFieldValuesEditor',
	component: CustomFieldValuesEditor,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		fields: FIELDS,
		// Overridden by `CustomFieldValuesEditorDemo`'s own state below —
		// required here only so every story satisfies the component's
		// required props.
		values: {},
		onChange: () => {},
	},
} satisfies Meta<typeof CustomFieldValuesEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

function CustomFieldValuesEditorDemo(args: Story['args']) {
	const [values, setValues] = useState<Record<string, unknown>>({});
	return (
		<CustomFieldValuesEditor
			{...args}
			fields={args?.fields ?? FIELDS}
			values={values}
			onChange={setValues}
		/>
	);
}

export const Default: Story = {
	render: (args) => <CustomFieldValuesEditorDemo {...args} />,
};

export const WithErrors: Story = {
	args: {
		errors: { floor: 'Floor is required.' },
	},
	render: (args) => <CustomFieldValuesEditorDemo {...args} />,
};
