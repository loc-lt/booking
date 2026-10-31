import type { FieldDefinition } from '@booking-core/api-client';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { useState } from 'react';
import { FieldDefinitionsEditor } from './FieldDefinitionsEditor';

const FIELDS: FieldDefinition[] = [
	{ key: 'floor', label: 'Floor', type: 'text', required: true },
	{
		key: 'equipment',
		label: 'Equipment',
		type: 'select',
		options: [
			{ value: 'whiteboard', label: 'Whiteboard' },
			{ value: 'tv', label: 'TV screen' },
		],
	},
];

const RESOURCE_TYPE_OPTIONS = [
	{ value: 'building-type', label: 'Building' },
	{ value: 'floor-type', label: 'Floor' },
];

const meta = {
	title: 'custom-fields/FieldDefinitionsEditor',
	component: FieldDefinitionsEditor,
	tags: ['autodocs'],
	parameters: { layout: 'padded' },
	args: {
		resourceTypeOptions: RESOURCE_TYPE_OPTIONS,
		// Overridden by `FieldDefinitionsEditorDemo`'s own state below —
		// required here only so every story satisfies the component's
		// required props.
		value: [],
		onChange: () => {},
	},
} satisfies Meta<typeof FieldDefinitionsEditor>;

export default meta;
type Story = StoryObj<typeof meta>;

function FieldDefinitionsEditorDemo(args: Story['args']) {
	const [fields, setFields] = useState<FieldDefinition[]>(args?.value ?? []);
	return <FieldDefinitionsEditor {...args} value={fields} onChange={setFields} />;
}

export const Empty: Story = {
	args: { value: [] },
	render: (args) => <FieldDefinitionsEditorDemo {...args} />,
};

export const WithFields: Story = {
	args: { value: FIELDS },
	render: (args) => <FieldDefinitionsEditorDemo {...args} />,
};
